from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from apps.avatar.schemas import OnboardingCompletedPayload
from apps.avatar.service import AvatarIngestService
from apps.benchmark.schemas import BenchmarkAvatarIngestRequest, BenchmarkAvatarIngestResponse


class BenchmarkAvatarIngestService:
    def __init__(
        self,
        session: AsyncSession,
        ingest_service_factory: Callable[[AsyncSession], AvatarIngestService] = AvatarIngestService,
    ):
        self.session = session
        self.ingest_service_factory = ingest_service_factory

    async def ingest(self, request: BenchmarkAvatarIngestRequest) -> BenchmarkAvatarIngestResponse:
        event = OnboardingCompletedPayload.model_validate(request.model_dump())
        ingest_service = self.ingest_service_factory(self.session)

        try:
            created = await ingest_service.ingest(event)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return BenchmarkAvatarIngestResponse(
            event_id=event.event_id,
            user_id=event.user_id,
            created=created,
        )

