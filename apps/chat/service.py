from __future__ import annotations

from dataclasses import dataclass
import re

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from apps.avatar.repository import AvatarRepository
from apps.chat.schemas import ChatHistoryItem
from core.config import settings
from core.embeddings import embed_text


@dataclass
class ChatResult:
    model: str
    answer: str
    used_contexts: list[str]


class ChatService:
    def __init__(self, session: AsyncSession, client: AsyncOpenAI | None = None):
        self.repo = AvatarRepository(session)
        self.client = client or AsyncOpenAI()

    async def generate(
        self,
        user_id: int,
        message: str,
        model: str | None = None,
        history: list[ChatHistoryItem] | None = None,
    ) -> ChatResult:
        chat_model = model or settings.CHAT_MODEL
        self._validate_model(chat_model)

        profile = await self.repo.get_profile_by_user_id(user_id)
        if profile is None:
            raise ValueError(f"avatar profile not found for user_id={user_id}")

        avatar_name = self._avatar_name(profile.nickname)
        if self._is_identity_question(message):
            return ChatResult(
                model=chat_model,
                answer=f"나는 {avatar_name}야.",
                used_contexts=[],
            )

        query_embedding = await self._embed_for_retrieval(message)
        contexts = await self.repo.find_similar_embeddings(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=settings.CHAT_TOP_K,
        )

        system_prompt = self._build_system_prompt(profile, contexts, avatar_name)
        chat_history = history or []
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._to_openai_history(chat_history))
        messages.append({"role": "user", "content": message})
        response = await self.client.responses.create(
            model=chat_model,
            input=messages,
        )
        answer = response.output_text.strip()
        return ChatResult(model=chat_model, answer=answer, used_contexts=contexts)

    @staticmethod
    def _validate_model(model: str) -> None:
        if model not in settings.ALLOWED_CHAT_MODELS:
            raise ValueError(f"model not allowed: {model}")

    async def _embed_for_retrieval(self, text: str) -> list[float]:
        return await embed_text(self.client, text)

    @staticmethod
    def _build_system_prompt(profile, contexts: list[str], avatar_name: str) -> str:
        personality = profile.personality or "자연스럽고 친근한"
        speech_style = profile.speech_style or "부드럽고 짧은"
        summary = profile.profile_summary or "추가 프로필 정보 없음"
        context_text = "\n\n".join(contexts) if contexts else "참고 컨텍스트 없음"

        return (
            "너는 사용자의 아바타 챗봇이다.\n"
            f"- 너의 이름: {avatar_name}\n"
            f"- 말투: {speech_style}\n"
            f"- 성격: {personality}\n"
            f"- 사용자 프로필 요약: {summary}\n"
            "- 답변 규칙: 한국어로 답하고, 너무 길지 않게 핵심부터 말해라.\n"
            f"- 정체성을 묻는 질문에는 반드시 '{avatar_name}'라고 소개해라.\n"
            "- 참고 컨텍스트(필요할 때만 활용):\n"
            f"{context_text}"
        )

    @staticmethod
    def _to_openai_history(history: list[ChatHistoryItem]) -> list[dict[str, str]]:
        mapped: list[dict[str, str]] = []
        for item in history:
            role = "assistant" if item.role == "AVATAR" else "user"
            mapped.append({"role": role, "content": item.content})
        return mapped

    @staticmethod
    def _avatar_name(nickname: str | None) -> str:
        normalized = nickname.strip() if nickname is not None else ""
        if not normalized:
            return "사용자의 아바타"
        return f"{normalized}의 아바타"

    @staticmethod
    def _is_identity_question(message: str) -> bool:
        normalized = re.sub(r"\s+", "", message.lower())
        patterns = [
            r"누구(야|냐)?",
            r"정체가뭐",
            r"이름이뭐",
            r"넌누구",
            r"너는누구",
            r"whoareyou",
        ]
        return any(re.search(pattern, normalized) for pattern in patterns)
