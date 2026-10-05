import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.infrastructure.database.session import Base, engine, SessionLocal
from app.infrastructure.database.models import SocialPostDB, PersonDB, CustomerDB
from datetime import datetime, timezone

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_clean_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    with client:
        yield db
    db.close()


def test_api_security_guard():
    # 1. Missing header -> 401
    resp = client.get("/api/v1/posts")
    assert resp.status_code == 401

    # 2. Invalid header -> 403
    resp = client.get("/api/v1/posts", headers={"X-App-Session-Token": "wrong-token"})
    assert resp.status_code == 403

    # 3. Valid header -> 200
    headers = {"X-App-Session-Token": settings.SESSION_TOKEN}
    resp = client.get("/api/v1/posts", headers=headers)
    assert resp.status_code == 200


def test_scan_lifecycle(monkeypatch):
    async def pending_discover(*args):
        import asyncio

        await asyncio.sleep(3600)
        return []

    monkeypatch.setattr("app.api.v1.scans.discover", pending_discover)
    headers = {"X-App-Session-Token": settings.SESSION_TOKEN}
    # 1. Create scan job
    create_payload = {
        "platform": "FACEBOOK",
        "keywords": ["cần lắp wifi", "lắp mạng fpt"],
        "max_posts": 200,
        "max_age_hours": 12,
        "blacklist_mode": "HARD_BLACKLIST",
    }
    resp = client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    # 2. Get scan job
    resp = client.get(f"/api/v1/scans/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "RUNNING"

    # 3. Pause
    resp = client.post(f"/api/v1/scans/{job_id}/pause", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"

    # 4. Resume
    resp = client.post(f"/api/v1/scans/{job_id}/resume", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "RUNNING"

    # 5. Stop
    resp = client.post(f"/api/v1/scans/{job_id}/stop", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "STOPPED"


def test_person_to_customer_flow():
    headers = {"X-App-Session-Token": settings.SESSION_TOKEN}
    db = SessionLocal()
    try:
        # Create Person
        person = PersonDB(
            display_name="Vu Thi Thuy", source_type="FACEBOOK", contact_quality_score=85
        )
        db.add(person)
        db.commit()
        person_id = person.id
    finally:
        db.close()

    # Convert to Customer
    convert_payload = {
        "need_type": "COMBO",
        "property_type": "HOUSE",
        "province": "Hà Nội",
        "urgency": "HIGH",
        "initial_opportunity_title": "Lắp Combo WiFi + 3 Camera",
        "expected_revenue": 3500000.0,
    }
    resp = client.post(
        f"/api/v1/persons/{person_id}/convert-customer",
        json=convert_payload,
        headers=headers,
    )
    assert resp.status_code == 200
    customer_id = resp.json()["customer_id"]

    # Get Customer 360
    resp = client.get(f"/api/v1/customers/{customer_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Vu Thi Thuy"
    assert data["need_type"] == "COMBO"
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["expected_revenue"] == 3500000.0
