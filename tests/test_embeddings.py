from __future__ import annotations

import pytest

from core import embeddings


class ExplodingClient:
    class embeddings:
        @staticmethod
        async def create(*args, **kwargs):
            raise AssertionError("OpenAI embeddings.create should not be called in fake benchmark mode")


@pytest.mark.asyncio
async def test_embed_text_returns_deterministic_fake_vector_when_benchmark_mode_enabled(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "BENCHMARK_FAKE_EMBEDDING", True)
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_DIM", 8)

    first = await embeddings.embed_text(ExplodingClient(), "same-input")
    second = await embeddings.embed_text(ExplodingClient(), "same-input")
    third = await embeddings.embed_text(ExplodingClient(), "different-input")

    assert len(first) == 8
    assert first == second
    assert first != third
    assert all(-1.0 <= value <= 1.0 for value in first)


@pytest.mark.asyncio
async def test_embed_text_calls_openai_when_benchmark_mode_disabled(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "BENCHMARK_FAKE_EMBEDDING", False)
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_MODEL", "fake-model")
    monkeypatch.setattr(embeddings.settings, "EMBEDDING_DIM", 4)

    class DummyData:
        embedding = [0.1, 0.2, 0.3, 0.4]

    class DummyResponse:
        data = [DummyData()]

    class DummyClient:
        class embeddings:
            @staticmethod
            async def create(*args, **kwargs):
                assert kwargs["model"] == "fake-model"
                assert kwargs["input"] == "hello"
                assert kwargs["dimensions"] == 4
                return DummyResponse()

    result = await embeddings.embed_text(DummyClient(), "hello")

    assert result == [0.1, 0.2, 0.3, 0.4]
