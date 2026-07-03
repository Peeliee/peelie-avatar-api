from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


class FakeChatService:
    def __init__(self, session):
        self.session = session

    async def generate(self, user_id: int, message: str, history=None):
        raise ValueError(f"avatar profile not found for user_id={user_id}")

    async def stream_generate(self, user_id: int, message: str, history=None):
        yield type(
            "Event",
            (),
            {"event": "meta", "data": {"user_id": user_id, "model": "gpt-4.1-mini-2025-04-14", "used_contexts": []}},
        )()
        yield type("Event", (), {"event": "delta", "data": {"content": "안"}})()
        yield type("Event", (), {"event": "delta", "data": {"content": "녕"}})()
        yield type(
            "Event",
            (),
            {
                "event": "done",
                "data": {
                    "user_id": user_id,
                    "model": "gpt-4.1-mini-2025-04-14",
                    "answer": "안녕",
                    "used_contexts": [],
                },
            },
        )()


def test_chat_router_returns_400_when_profile_missing(monkeypatch):
    monkeypatch.setattr("apps.chat.router.ChatService", FakeChatService)

    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        json={"user_id": 12345, "message": "안녕"},
    )

    assert response.status_code == 400
    assert "avatar profile not found" in response.json()["detail"]


def test_chat_stream_router_returns_sse_events(monkeypatch):
    monkeypatch.setattr("apps.chat.router.ChatService", FakeChatService)

    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/stream",
        json={"user_id": 1, "message": "안녕"},
    ) as response:
        body = response.text

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'event: meta' in body
    assert 'event: delta' in body
    assert 'event: done' in body
    assert '"answer": "안녕"' in body


class FakeFailingStreamChatService:
    def __init__(self, session):
        self.session = session

    async def generate(self, user_id: int, message: str, history=None):
        raise ValueError(f"avatar profile not found for user_id={user_id}")

    async def stream_generate(self, user_id: int, message: str, history=None):
        raise ValueError(f"avatar profile not found for user_id={user_id}")
        yield


def test_chat_stream_router_returns_error_event_when_stream_fails(monkeypatch):
    monkeypatch.setattr("apps.chat.router.ChatService", FakeFailingStreamChatService)

    client = TestClient(app)
    with client.stream(
        "POST",
        "/v1/chat/stream",
        json={"user_id": 12345, "message": "안녕"},
    ) as response:
        body = response.text

    assert response.status_code == 200
    assert 'event: error' in body
    assert 'avatar profile not found' in body
