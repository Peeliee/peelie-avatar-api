from __future__ import annotations

from fastapi import FastAPI

from apps.benchmark.router import router as benchmark_router
from apps.chat.router import router as chat_router

app = FastAPI(title="peelie-avatar-api")
app.include_router(chat_router)
app.include_router(benchmark_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
