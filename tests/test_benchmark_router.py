from __future__ import annotations

from fastapi.testclient import TestClient

import apps.benchmark.router as benchmark_router_module
from main import app


class FakeBenchmarkService:
    def __init__(self, session):
        self.session = session

    async def ingest(self, request):
        return type(
            "BenchmarkAvatarIngestResponse",
            (),
            {
                "event_id": request.event_id,
                "user_id": request.user_id,
                "created": True,
            },
        )()


def test_benchmark_router_accepts_internal_ingest_request(monkeypatch):
    monkeypatch.setattr(benchmark_router_module, "BenchmarkAvatarIngestService", FakeBenchmarkService)

    client = TestClient(app)
    response = client.post(
        "/internal/benchmark/avatar/ingest",
        json={
            "event_id": "evt_100",
            "user_id": 100,
            "nickname": "테스터",
            "occurred_at": "2026-03-19T12:00:00",
            "answers": [
                {
                    "question_id": 1,
                    "purpose": "USER_INFO",
                    "answer": "집에서 쉬는 편",
                    "option_tag": None,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "event_id": "evt_100",
        "user_id": 100,
        "created": True,
    }
