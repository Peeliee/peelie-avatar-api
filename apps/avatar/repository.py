from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.avatar.models import AvatarEmbedding, AvatarProfile


class AvatarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def has_processed_event(self, event_id: str) -> bool:
        query: Select[tuple[int]] = select(AvatarProfile.id).where(AvatarProfile.event_id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def upsert_profile(
        self,
        event_id: str,
        user_id: int,
        nickname: str | None,
        personality: str | None,
        speech_style: str | None,
        profile_summary: str | None,
    ) -> None:
        stmt = insert(AvatarProfile).values(
            event_id=event_id,
            user_id=user_id,
            nickname=nickname,
            personality=personality,
            speech_style=speech_style,
            profile_summary=profile_summary,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "event_id": event_id,
                "nickname": nickname,
                "personality": personality,
                "speech_style": speech_style,
                "profile_summary": profile_summary,
            },
        )
        await self.session.execute(stmt)

    async def upsert_embedding(
        self,
        event_id: str,
        user_id: int,
        category: str,
        content: str,
        embedding: list[float],
    ) -> None:
        stmt = insert(AvatarEmbedding).values(
            event_id=event_id,
            user_id=user_id,
            category=category,
            content=content,
            embedding=embedding,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "category"],
            set_={"event_id": event_id, "content": content, "embedding": embedding},
        )
        await self.session.execute(stmt)
