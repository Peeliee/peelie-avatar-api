from __future__ import annotations

import hashlib

from openai import AsyncOpenAI

from core.config import settings


def _fake_embedding(text: str) -> list[float]:
    # Deterministic pseudo-vector for benchmark runs. This preserves the
    # retrieval flow without paying for external embedding calls.
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < settings.EMBEDDING_DIM:
        for byte in seed:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == settings.EMBEDDING_DIM:
                break
        seed = hashlib.sha256(seed).digest()
    return values


async def embed_text(client: AsyncOpenAI, text: str) -> list[float]:
    if settings.BENCHMARK_FAKE_EMBEDDING:
        return _fake_embedding(text)

    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
        dimensions=settings.EMBEDDING_DIM,
    )
    return response.data[0].embedding
