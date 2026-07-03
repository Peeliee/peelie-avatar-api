from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from apps.avatar.repository import AvatarRepository
from apps.chat.schemas import ChatHistoryItem, ChatStreamEvent
from core.config import settings
from core.embeddings import embed_text


@dataclass
class ChatResult:
    model: str
    answer: str
    used_contexts: list[str]


@dataclass
class PreparedChatRequest:
    model: str
    messages: list[dict[str, str]]
    used_contexts: list[str]
    immediate_answer: str | None = None


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
        prepared = await self._prepare_request(
            user_id=user_id,
            message=message,
            model=model,
            history=history,
        )
        if prepared.immediate_answer is not None:
            return ChatResult(
                model=prepared.model,
                answer=prepared.immediate_answer,
                used_contexts=prepared.used_contexts,
            )

        response = await self.client.responses.create(
            model=prepared.model,
            input=prepared.messages,
        )
        answer = response.output_text.strip()
        return ChatResult(model=prepared.model, answer=answer, used_contexts=prepared.used_contexts)

    async def stream_generate(
        self,
        user_id: int,
        message: str,
        model: str | None = None,
        history: list[ChatHistoryItem] | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        prepared = await self._prepare_request(
            user_id=user_id,
            message=message,
            model=model,
            history=history,
        )

        yield ChatStreamEvent(
            event="meta",
            data={
                "user_id": user_id,
                "model": prepared.model,
                "used_contexts": prepared.used_contexts,
            },
        )

        if prepared.immediate_answer is not None:
            yield ChatStreamEvent(event="delta", data={"content": prepared.immediate_answer})
            yield ChatStreamEvent(
                event="done",
                data={
                    "user_id": user_id,
                    "model": prepared.model,
                    "answer": prepared.immediate_answer,
                    "used_contexts": prepared.used_contexts,
                },
            )
            return

        answer_parts: list[str] = []
        final_response = None
        async with self.client.responses.stream(
            model=prepared.model,
            input=prepared.messages,
        ) as stream:
            async for event in stream:
                delta = self._extract_output_text_delta(event)
                if not delta:
                    continue

                answer_parts.append(delta)
                yield ChatStreamEvent(event="delta", data={"content": delta})

            final_response = await stream.get_final_response()

        final_answer = "".join(answer_parts).strip()
        if not final_answer and final_response is not None:
            final_answer = getattr(final_response, "output_text", "").strip()

        yield ChatStreamEvent(
            event="done",
            data={
                "user_id": user_id,
                "model": prepared.model,
                "answer": final_answer,
                "used_contexts": prepared.used_contexts,
            },
        )

    @staticmethod
    def _validate_model(model: str) -> None:
        if model not in settings.ALLOWED_CHAT_MODELS:
            raise ValueError(f"model not allowed: {model}")

    async def _embed_for_retrieval(self, text: str) -> list[float]:
        return await embed_text(self.client, text)

    async def _prepare_request(
        self,
        user_id: int,
        message: str,
        model: str | None,
        history: list[ChatHistoryItem] | None,
    ) -> PreparedChatRequest:
        chat_model = model or settings.CHAT_MODEL
        self._validate_model(chat_model)

        profile = await self.repo.get_profile_by_user_id(user_id)
        if profile is None:
            raise ValueError(f"avatar profile not found for user_id={user_id}")

        avatar_name = self._avatar_name(profile.nickname)
        if self._is_identity_question(message):
            return PreparedChatRequest(
                model=chat_model,
                messages=[],
                used_contexts=[],
                immediate_answer=f"나는 {avatar_name}야.",
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
        return PreparedChatRequest(
            model=chat_model,
            messages=messages,
            used_contexts=contexts,
        )

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
            "- 답변 규칙: 한국어로 답하고, 사용자의 질문을 파악하고 질문에 대한 한가지의 주제만 대답해라.\n"
            "- 답변 규칙: 사용자가 짧게 인사만 하거나 가벼운 호응만 하면, 인사나 짧은 반응만 자연스럽게 답하고 참고 컨텍스트를 먼저 꺼내지 마라.\n"
            "- 답변 규칙: 참고 컨텍스트는 사용자의 현재 질문에 직접 관련이 있을 때만 아주 조금 반영하라.\n"
            "- 답변 규칙: 사용자가 먼저 묻지 않은 일정, 취향, 과거 대화 내용을 갑자기 먼저 꺼내지 마라.\n"
            f"- 정체성을 묻는 질문에는 반드시 '{avatar_name}'라고 소개해라.\n"
            "- 참고 컨텍스트(필요할 때만 활용):\n"
            f"{context_text}"
        )

    @staticmethod
    def _extract_output_text_delta(event: Any) -> str | None:
        if isinstance(event, dict):
            if event.get("type") == "response.output_text.delta":
                delta = event.get("delta")
                return delta if isinstance(delta, str) else None
            return None

        if getattr(event, "type", None) != "response.output_text.delta":
            return None

        delta = getattr(event, "delta", None)
        return delta if isinstance(delta, str) else None

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
