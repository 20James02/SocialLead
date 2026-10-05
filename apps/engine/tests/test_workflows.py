import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings, Settings
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import (
    PersonDB,
    CustomerDB,
    OpportunityDB,
    CareTaskDB,
    SocialPostDB,
    PersonPhoneDB,
    PermissionDB,
    ConversationDB,
    SavedPostDB,
    CampaignRecipientDB,
)
from app.modules.scanner.retention import retention_cleaner
from app.modules.campaign.consent_manager import ConsentGovernance
from app.integrations.zalo.adapter import zalo_personal, zalo_oa
from app.integrations.official import IntegrationUnavailable


@pytest.fixture
def client():
    with TestClient(app, headers={"X-App-Session-Token": settings.SESSION_TOKEN}) as c:
        yield c


def source(external_id="post-1", **changes):
    return {
        "platform": "FACEBOOK",
        "external_id": external_id,
        "author_id": "author-1",
        "author_name": "Nguyễn Minh Anh",
        "url": "https://www.facebook.com/posts/123",
        "content": "Nhà mình 3 tầng ở Hà Nội cần lắp wifi và camera gấp hôm nay. 0989626638",
        "posted_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **changes,
    }


def import_source(client, posts=None):
    response = client.post(
        "/api/v1/scans/import",
        json={"platform": "FACEBOOK", "posts": posts or [source()]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_customer(client, name="Nguyễn Minh Anh", phone="0989626638"):
    response = client.post(
        "/api/v1/persons", json={"display_name": name, "phone": phone}
    )
    assert response.status_code == 201, response.text
    person_id = response.json()["id"]
    response = client.post(
        f"/api/v1/persons/{person_id}/convert-customer",
        json={"need_type": "COMBO", "initial_opportunity_title": "WiFi + Camera"},
    )
    assert response.status_code == 200, response.text
    return person_id, response.json()["customer_id"]


def test_complete_import_to_customer_care_search_flow(client):
    imported = import_source(
        client,
        [
            source(
                comments=[
                    {
                        "external_id": "c1",
                        "author_name": "Trần An",
                        "author_url": "https://www.facebook.com/456",
                        "content": "Cần lắp wifi gấp 0911000111",
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            )
        ],
    )
    assert imported["status"] == "COMPLETED" and imported["qualified_count"] == 1
    post = client.get("/api/v1/posts").json()[0]
    analysis = client.get(f"/api/v1/posts/{post['id']}/analysis").json()
    assert analysis["score"]["overall_lead_score"] >= 70
    assert analysis["phones"][0]["is_verified"] is False
    assert analysis["phones"][0]["source_url"] == post["url"]
    response = client.post(f"/api/v1/posts/{post['id']}/promote")
    assert response.status_code == 200, response.text
    person_id = response.json()["person_id"]
    assert (
        client.post(f"/api/v1/posts/{post['id']}/promote").json()["person_id"]
        == person_id
    )
    response = client.post(
        f"/api/v1/persons/{person_id}/convert-customer",
        json={
            "need_type": "COMBO",
            "initial_opportunity_title": "Camera",
            "expected_revenue": 3000000,
        },
    )
    assert response.status_code == 200
    customer_id = response.json()["customer_id"]
    assert (
        client.post(
            f"/api/v1/persons/{person_id}/notes",
            json={"content": "Khách hẹn kiểm tra hạ tầng Discovery"},
        ).status_code
        == 201
    )
    assert client.get("/api/v1/search", params={"q": "Discovery"}).json()
    assert (
        client.get("/api/v1/search", params={"q": "0989.626.638"}).json()[0][
            "entity_type"
        ]
        == "PERSON"
    )
    task = client.post(
        "/api/v1/care-tasks",
        json={
            "customer_id": customer_id,
            "title": "Gọi tư vấn",
            "scheduled_at": (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).isoformat(),
        },
    )
    assert task.status_code == 201 and task.json()["is_overdue"]
    assert (
        client.patch(f"/api/v1/care-tasks/{task.json()['id']}/complete").status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/customers/{customer_id}").json()["next_care_date"] is None
    )
    assert client.get("/api/v1/dashboard").json()["customers"] == 1
    export = client.get("/api/v1/export/customers")
    assert export.status_code == 200 and "Nguyễn Minh Anh" in export.text
    comments = client.get(f"/api/v1/posts/{post['id']}/comments").json()
    promoted = client.post(
        f"/api/v1/posts/{post['id']}/comments/{comments[0]['id']}/promote"
    )
    assert promoted.status_code == 200
    assert (
        client.get(f"/api/v1/persons/{promoted.json()['person_id']}").json()["phones"][
            0
        ]["source_type"]
        == "SOCIAL_COMMENT"
    )


def test_dedup_survives_new_scan_and_uses_canonical_content(client):
    original = source()
    assert import_source(client, [original])["matched_count"] == 1
    assert import_source(client, [original])["matched_count"] == 0
    assert (
        import_source(
            client, [{**original, "external_id": "same-content-different-id"}]
        )["matched_count"]
        == 0
    )
    assert len(client.get("/api/v1/posts").json()) == 1


@pytest.mark.parametrize(
    "kind,value",
    [
        ("KEYWORD", "camera"),
        ("PROFILE", "author-1"),
        ("PHONE", "0989626638"),
        ("DOMAIN", "facebook.com"),
    ],
)
def test_persistent_hard_blacklist_blocks_import(client, kind, value):
    assert (
        client.post(
            "/api/v1/blacklist", json={"entity_type": kind, "value": value}
        ).status_code
        == 201
    )
    result = import_source(client)
    assert result["matched_count"] == 0 and result["spam_count"] == 1


def test_soft_blacklist_keeps_post_but_penalizes_score(client):
    client.post(
        "/api/v1/blacklist",
        json={"entity_type": "KEYWORD", "value": "wifi", "mode": "SOFT_BLACKLIST"},
    )
    assert import_source(client)["matched_count"] == 1
    assert client.get("/api/v1/posts").json()[0]["lead_score"] == 0


def test_age_limits_and_invalid_platform_import(client):
    result = import_source(
        client,
        [
            source(
                posted_at=(datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
            )
        ],
    )
    assert result["matched_count"] == 0
    response = client.post(
        "/api/v1/scans/import", json={"platform": "THREADS", "posts": [source()]}
    )
    assert response.status_code == 422
    assert client.post("/api/v1/scans", json={"keywords": [" "]}).status_code == 422


def test_phone_and_saved_filters_are_applied_before_pagination(client):
    a = client.post(
        "/api/v1/persons", json={"display_name": "Có điện thoại", "phone": "0989626638"}
    ).json()["id"]
    client.post("/api/v1/persons", json={"display_name": "Không có điện thoại"})
    assert client.get("/api/v1/persons?has_phone=true&limit=1").json()[0]["id"] == a
    first, second = (
        source(),
        source(
            "post-2",
            content="Cần lắp wifi hôm nay",
            posted_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        ),
    )
    import_source(client, [first, second])
    posts = client.get("/api/v1/posts").json()
    client.post(f"/api/v1/posts/{posts[1]['id']}/save")
    assert (
        client.get("/api/v1/posts?is_saved=true&limit=1").json()[0]["id"]
        == posts[1]["id"]
    )


def test_care_validation_and_next_date_recalculation(client):
    person_id, customer_id = create_customer(client)
    now = datetime.now(timezone.utc)
    one = client.post(
        "/api/v1/care-tasks",
        json={
            "customer_id": customer_id,
            "title": "Task 1",
            "scheduled_at": now.isoformat(),
        },
    ).json()
    later = now + timedelta(days=3)
    two = client.post(
        "/api/v1/care-tasks",
        json={
            "customer_id": customer_id,
            "title": "Task 2",
            "scheduled_at": later.isoformat(),
        },
    ).json()
    assert client.patch(f"/api/v1/care-tasks/{one['id']}/complete").status_code == 200
    detail = client.get(f"/api/v1/customers/{customer_id}").json()
    assert (
        datetime.fromisoformat(detail["next_care_date"]).replace(tzinfo=timezone.utc)
        == later
    )
    assert (
        client.post(
            "/api/v1/care-tasks",
            json={
                "customer_id": "missing",
                "title": "Bad",
                "scheduled_at": now.isoformat(),
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/care-tasks",
            json={
                "customer_id": customer_id,
                "title": "Naive",
                "scheduled_at": "2026-10-05T10:00:00",
            },
        ).status_code
        == 422
    )


def test_merge_two_customers_preserves_opportunities_tasks_consent(client):
    p1, c1 = create_customer(client, "Primary")
    p2, c2 = create_customer(client, "Duplicate", "0911000111")
    task = client.post(
        "/api/v1/care-tasks",
        json={
            "customer_id": c2,
            "title": "Keep me",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
        },
    ).json()
    client.put(
        f"/api/v1/persons/{p1}/permission",
        json={"source": "Opt in", "marketing_allowed": True, "zalo_allowed": True},
    )
    client.put(
        f"/api/v1/persons/{p2}/permission", json={"source": "Opt out", "opt_out": True}
    )
    client.put(f"/api/v1/persons/{p2}/labels", json={"labels": ["VIP"]})
    response = client.post(
        "/api/v1/persons/merge",
        json={
            "primary_person_id": p1,
            "duplicate_person_id": p2,
            "merge_reason": 'Same person "confirmed"',
        },
    )
    assert response.status_code == 200, response.text
    assert len(client.get(f"/api/v1/customers/{c1}").json()["opportunities"]) == 2
    assert client.get(f"/api/v1/persons/{p1}").json()["permission"]["opt_out"]
    assert "VIP" in client.get(f"/api/v1/persons/{p1}").json()["labels"]
    assert client.get("/api/v1/care-tasks").json()[0]["customer_id"] == c1
    assert client.get(f"/api/v1/customers/{c2}").status_code == 404


def test_backup_restore_and_path_guards(client):
    create_customer(client, "Before backup")
    result = client.post("/api/v1/backup/create")
    assert result.status_code == 200
    filename = result.json()["backup"]["filename"]
    create_customer(client, "After backup")
    assert len(client.get("/api/v1/customers").json()) == 2
    result = client.post("/api/v1/backup/restore", json={"filename": filename})
    assert result.status_code == 200, result.text
    assert len(client.get("/api/v1/customers").json()) == 1
    assert len(client.get("/api/v1/backup").json()) >= 2
    assert (
        client.post(
            "/api/v1/backup/restore", json={"filename": "../scansocial.db"}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/search", params={"q": "After"}).json() == []


def test_retention_preserves_promoted_posts_and_cleans_search(client):
    import_source(
        client,
        [source(), source("post-2", author_id="b", content="temporary wifi text")],
    )
    posts = client.get("/api/v1/posts").json()
    saved = next(
        p
        for p in posts
        if p["author_name"] == "Nguyễn Minh Anh" and p["phone_extracted"]
    )
    client.post(f"/api/v1/posts/{saved['id']}/promote")
    with SessionLocal() as db:
        db.query(SocialPostDB).update(
            {"detected_at": datetime.now(timezone.utc) - timedelta(days=10)}
        )
        db.commit()
        assert retention_cleaner.cleanup_expired_raw_scans(db) == 1
    assert client.get("/api/v1/search", params={"q": "temporary"}).json() == []
    assert len(client.get("/api/v1/posts").json()) == 1


def test_missing_provider_fails_job_with_actionable_status(client, monkeypatch):
    monkeypatch.setattr("app.integrations.official.vault.get_secret", lambda key: None)
    result = client.post(
        "/api/v1/scans", json={"platform": "THREADS", "keywords": ["wifi"]}
    ).json()
    for _ in range(50):
        job = client.get(f"/api/v1/scans/{result['id']}").json()
        if job["status"] == "FAILED":
            break
        time.sleep(0.01)
    assert job["status"] == "FAILED" and "access token" in job["error_message"]
    assert client.post(f"/api/v1/scans/{job['id']}/resume").status_code == 409


def test_live_event_auth_and_import_notification(client):
    with client.websocket_connect(f"/ws/live?token={settings.SESSION_TOKEN}") as ws:
        imported = import_source(client)
        event = ws.receive_json()
        assert (
            event["event_type"] == "SCAN_COMPLETED"
            and event["payload"]["id"] == imported["id"]
        )
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/live?token=wrong"):
            pass
    assert (
        client.get(
            "/api/v1/persons", headers={b"X-App-Session-Token": b"\xc3\xa9"}
        ).status_code
        == 403
    )


def test_loopback_cors_and_invalid_values(client):
    with pytest.raises(ValueError):
        Settings(HOST="0.0.0.0")
    assert (
        client.post(
            "/api/v1/persons", json={"display_name": " ", "phone": "invalid"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/persons", json={"display_name": "Test", "phone": "0123"}
        ).status_code
        == 422
    )
    result = client.options(
        "/api/v1/posts",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in result.headers


def test_zalo_assisted_log_never_claims_to_send(client):
    p, c = create_customer(client)
    result = client.post(
        "/api/v1/conversations",
        json={
            "person_id": p,
            "title": "Zalo care",
            "external_conversation_id": "123456",
        },
    )
    assert result.status_code == 201
    conv = result.json()["id"]
    response = client.post(
        f"/api/v1/conversations/{conv}/messages", json={"content": "Tôi cần lắp camera"}
    )
    assert response.json()["status"] == "RECORDED"
    draft = client.post(f"/api/v1/conversations/{conv}/suggestion").json()
    assert draft["requires_manual_send"] and draft["draft"]
    with pytest.raises(IntegrationUnavailable):
        asyncio.run(zalo_personal.send_message("123", "Hello"))


def test_campaign_blocks_without_consent_and_does_not_send(client):
    p, c = create_customer(client)
    campaign = client.post(
        "/api/v1/campaigns",
        json={"name": "Care", "message_template": "Chào {name}", "customer_ids": [c]},
    ).json()["id"]
    preview = client.get(f"/api/v1/campaigns/{campaign}/preview").json()[0]
    assert not preview["eligible"]
    assert (
        client.post(
            f"/api/v1/campaigns/{campaign}/recipients/{preview['id']}/send",
            json={"reviewed": True},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/campaigns/{campaign}/recipients/{preview['id']}/send",
            json={"reviewed": False},
        ).status_code
        == 422
    )


def test_vietnam_quiet_hours_use_customer_timezone():
    assert ConsentGovernance.is_in_quiet_hours(
        datetime(2026, 10, 5, 14, tzinfo=timezone.utc)
    )  # 21:00 VN
    assert not ConsentGovernance.is_in_quiet_hours(
        datetime(2026, 10, 5, 1, tzinfo=timezone.utc)
    )  # 08:00 VN
    assert ConsentGovernance.is_in_quiet_hours(
        datetime(2026, 10, 5, 0, 59, tzinfo=timezone.utc)
    )
