from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


class FakeChatService:
    def __init__(self, session):
        self.session = session

    async def generate(self, user_id: int, message: str, history=None):
        raise ValueError(f"avatar profile not found for user_id={user_id}")


def test_chat_router_returns_400_when_profile_missing(monkeypatch):
    monkeypatch.setattr("apps.chat.router.ChatService", FakeChatService)

    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        json={"user_id": 12345, "message": "안녕"},
    )

    assert response.status_code == 400
    assert "avatar profile not found" in response.json()["detail"]
