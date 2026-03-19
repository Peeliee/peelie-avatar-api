from __future__ import annotations

from fastapi import APIRouter

from apps.benchmark.schemas import BenchmarkAvatarIngestRequest, BenchmarkAvatarIngestResponse
from apps.benchmark.service import BenchmarkAvatarIngestService
from core.db import DbSessionDep

router = APIRouter(prefix="/internal/benchmark/avatar", tags=["benchmark"])


@router.post("/ingest", response_model=BenchmarkAvatarIngestResponse)
async def ingest(request: BenchmarkAvatarIngestRequest, session: DbSessionDep) -> BenchmarkAvatarIngestResponse:
    service = BenchmarkAvatarIngestService(session)
    return await service.ingest(request)

