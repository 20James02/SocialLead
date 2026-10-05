import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from app.integrations.official import discover, fetch_comments, IntegrationUnavailable
from app.integrations.zalo.adapter import zalo_oa
from app.modules.ai.provider import LocalOllamaProvider
from app.modules.scanner.blacklist import BlacklistEvaluator
from app.domain.models import BlacklistEntityType, BlacklistMode


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    mock = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original(transport=mock, **kwargs)
    )
    monkeypatch.setattr(
        "app.integrations.official.vault.get_secret", lambda key: "test-official-token"
    )


def test_threads_uses_all_keywords_and_never_follows_foreign_pagination_url(
    monkeypatch,
):
    calls = []

    def handler(request):
        calls.append(request)
        keyword = request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": keyword,
                        "username": "alice",
                        "text": "cần lắp wifi",
                        "permalink": "https://www.threads.net/@alice/post/example",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            },
        )

    transport(monkeypatch, handler)
    result = asyncio.run(discover("THREADS", ["wifi", "camera"], 2))
    assert len(result) == 2 and [r.url.params["q"] for r in calls] == ["wifi", "camera"]
    assert all(
        r.url.host == "graph.threads.net"
        and r.headers["authorization"] == "Bearer test-official-token"
        for r in calls
    )


def test_official_rate_limit_is_a_failure_without_retry(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": {"message": "Rate limited"}})

    transport(monkeypatch, handler)
    with pytest.raises(IntegrationUnavailable, match="HTTP 429"):
        asyncio.run(discover("THREADS", ["wifi"], 20))
    assert len(calls) == 1


def test_official_comments_keep_author_and_provenance(monkeypatch):
    def handler(request):
        assert request.url.path.endswith("/123/comments")
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "c1",
                        "from": {"id": "author-1", "name": "Nguyễn An"},
                        "message": "Cần wifi",
                        "created_time": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            },
        )

    transport(monkeypatch, handler)
    comments = asyncio.run(fetch_comments("FACEBOOK", "123"))
    assert comments[0].author_id == "author-1"
    with pytest.raises(IntegrationUnavailable):
        asyncio.run(fetch_comments("FACEBOOK", "../../private"))


@pytest.mark.parametrize(
    "body,expected",
    [
        ({"error": 0, "data": {"message_id": "m1"}}, True),
        ({"error": -1}, False),
        ({"error": 0}, False),
    ],
)
def test_zalo_never_reports_success_without_delivery_confirmation(
    monkeypatch, body, expected
):
    def handler(request):
        assert request.url.host == "openapi.zalo.me"
        assert request.headers["access_token"] == "test-official-token"
        return httpx.Response(200, json=body)

    transport(monkeypatch, handler)
    assert asyncio.run(zalo_oa.send_message("123456", "Tư vấn")) is expected


def test_ollama_falls_back_for_invalid_model_response(monkeypatch):
    transport(monkeypatch, lambda request: httpx.Response(200, json={"response": None}))
    draft = asyncio.run(
        LocalOllamaProvider().generate_reply_suggestion("Khách A", "Tôi cần WiFi")
    )
    assert "địa chỉ" in draft


def test_regex_blacklist_is_validated_and_bounded():
    rules = BlacklistEvaluator()
    rules.add_rule(
        BlacklistEntityType.REGEX, r"cho\s+vay", BlacklistMode.HARD_BLACKLIST, "Loans"
    )
    assert rules.evaluate(content="CHO    VAY nhanh")[0]
    rules.remove_rule(BlacklistEntityType.REGEX, r"cho\s+vay")
    assert not rules.evaluate(content="CHO VAY")[0]
