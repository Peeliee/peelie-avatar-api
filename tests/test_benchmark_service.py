from __future__ import annotations

import asyncio

import pytest

from apps.benchmark.schemas import BenchmarkAvatarIngestRequest
from apps.benchmark.service import BenchmarkAvatarIngestService


class DummySession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class DummyIngestService:
    def __init__(self, session):
        self.session = session

    async def ingest(self, event):
        self.event = event
        return True


def test_benchmark_avatar_ingest_service_commits_and_returns_response():
    session = DummySession()
    request = BenchmarkAvatarIngestRequest(
        event_id="evt_1",
        user_id=10,
        nickname="테스터",
        occurred_at="2026-03-19T12:00:00",
        answers=[
            {
                "question_id": 1,
                "purpose": "USER_INFO",
                "answer": "주말 집콕",
                "option_tag": None,
            }
        ],
    )

    service = BenchmarkAvatarIngestService(session, ingest_service_factory=DummyIngestService)
    result = asyncio.run(service.ingest(request))

    assert session.committed is True
    assert session.rolled_back is False
    assert result.event_id == "evt_1"
    assert result.user_id == 10
    assert result.created is True


def test_benchmark_avatar_ingest_service_rolls_back_on_error():
    session = DummySession()
    request = BenchmarkAvatarIngestRequest(
        event_id="evt_2",
        user_id=11,
        answers=[],
    )

    class ExplodingIngestService:
        def __init__(self, session):
            self.session = session

        async def ingest(self, event):
            raise RuntimeError("boom")

    service = BenchmarkAvatarIngestService(session, ingest_service_factory=ExplodingIngestService)

    with pytest.raises(RuntimeError):
        asyncio.run(service.ingest(request))

    assert session.committed is False
    assert session.rolled_back is True
