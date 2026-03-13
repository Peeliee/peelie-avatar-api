from __future__ import annotations

from openai import AsyncOpenAI

from core.config import settings


async def embed_text(client: AsyncOpenAI, text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
        dimensions=settings.EMBEDDING_DIM,
    )
    return response.data[0].embedding
