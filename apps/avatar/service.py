from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.avatar.models import AvatarCategory
from apps.avatar.repository import AvatarRepository
from apps.avatar.schemas import AvatarChunk, OnboardingAnswer, OnboardingCompletedPayload
from core.config import settings


class AvatarIngestService:
    def __init__(self, session: AsyncSession):
        self.repo = AvatarRepository(session)

    async def ingest(self, event: OnboardingCompletedPayload) -> bool:
        if await self.repo.has_processed_event(event.event_id):
            return False

        speech_style, personality = self._extract_style_fields(event.answers)
        profile_summary = self._build_profile_summary(event.answers)
        await self.repo.upsert_profile(
            event_id=event.event_id,
            user_id=event.user_id,
            nickname=event.nickname,
            personality=personality,
            speech_style=speech_style,
            profile_summary=profile_summary,
        )

        chunks = self._build_chunks(event)
        for chunk in chunks:
            embedding = self._embed(chunk.content)
            await self.repo.upsert_embedding(
                event_id=event.event_id,
                user_id=event.user_id,
                category=chunk.category,
                content=chunk.content,
                embedding=embedding,
            )

        return True

    def _build_chunks(self, event: OnboardingCompletedPayload) -> list[AvatarChunk]:
        bucketed: dict[str, list[str]] = defaultdict(list)
        for answer in event.answers:
            text = answer.answer.strip()
            if not text:
                continue

            category = self._purpose_to_category(answer.purpose)
            rendered = text
            if category == AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value and answer.option_tag:
                rendered = f"{text} ({answer.option_tag})"
            bucketed[category].append(rendered)

        chunks: list[AvatarChunk] = []
        for category, values in bucketed.items():
            content = "\n".join(values).strip()
            if content:
                chunks.append(AvatarChunk(category=category, content=content))
        return chunks

    @staticmethod
    def _extract_style_fields(answers: list[OnboardingAnswer]) -> tuple[str | None, str | None]:
        style_answers = [
            answer
            for answer in answers
            if answer.purpose == AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value and answer.option_tag
        ]
        style_answers.sort(key=lambda item: item.question_id)

        speech_style = style_answers[0].option_tag if len(style_answers) >= 1 else None
        personality = style_answers[1].option_tag if len(style_answers) >= 2 else None
        return speech_style, personality

    @staticmethod
    def _build_profile_summary(answers: list[OnboardingAnswer]) -> str | None:
        targets = {
            AvatarCategory.USER_INTERESTS.value,
            AvatarCategory.USER_INFO.value,
        }
        summary_parts = [a.answer.strip() for a in answers if a.purpose in targets and a.answer.strip()]
        if not summary_parts:
            return None
        return "\n".join(summary_parts)

    @staticmethod
    def _purpose_to_category(purpose: str) -> str:
        if purpose == AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value:
            return AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value
        if purpose == AvatarCategory.USER_INTERESTS.value:
            return AvatarCategory.USER_INTERESTS.value
        if purpose == AvatarCategory.USER_INFO.value:
            return AvatarCategory.USER_INFO.value
        return AvatarCategory.OTHER.value

    @staticmethod
    def _embed(text: str) -> list[float]:
        dim = settings.EMBEDDING_DIM
        seed = text.encode("utf-8")

        values: list[float] = []
        nonce = 0
        while len(values) < dim:
            digest = hashlib.sha256(seed + nonce.to_bytes(4, "big")).digest()
            for b in digest:
                values.append((b / 255.0) * 2.0 - 1.0)
                if len(values) == dim:
                    break
            nonce += 1

        return values


def build_payload_from_stream(fields: dict[str, Any]) -> OnboardingCompletedPayload:
    answers_json = fields.get("answers_json")
    if isinstance(answers_json, str):
        answers_container = json.loads(answers_json)
    elif isinstance(answers_json, dict):
        answers_container = answers_json
    else:
        answers_container = {}

    normalized = {
        "event_id": str(fields["event_id"]),
        "user_id": int(fields["user_id"]),
        "nickname": fields.get("nickname"),
        "occurred_at": fields.get("occurred_at"),
        "answers": answers_container.get("answers", []),
    }
    return OnboardingCompletedPayload.model_validate(normalized)
