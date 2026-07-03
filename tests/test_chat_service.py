from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.chat.service import ChatService


class DummyProfile:
    nickname = "테스터"
    personality = "유쾌함"
    speech_style = "반말"
    profile_summary = "게임과 영화 좋아함"


class DummyRepo:
    async def get_profile_by_user_id(self, user_id: int):
        return DummyProfile()

    async def find_similar_embeddings(self, user_id: int, query_embedding: list[float], top_k: int):
        return ["컨텍스트A", "컨텍스트B"]


class DummyRepoNoProfile:
    async def get_profile_by_user_id(self, user_id: int):
        return None

    async def find_similar_embeddings(self, user_id: int, query_embedding: list[float], top_k: int):
        return []


class DummyRepoNoContexts:
    async def get_profile_by_user_id(self, user_id: int):
        return DummyProfile()

    async def find_similar_embeddings(self, user_id: int, query_embedding: list[float], top_k: int):
        return []


class DummyResponse:
    output_text = "테스트 응답"


class DummyEmbeddingData:
    embedding = [0.1] * 64


class DummyEmbeddingResponse:
    data = [DummyEmbeddingData()]


class DummyClient:
    class embeddings:
        @staticmethod
        async def create(*args, **kwargs):
            return DummyEmbeddingResponse()

    class responses:
        @staticmethod
        async def create(*args, **kwargs):
            return DummyResponse()

        @staticmethod
        def stream(*args, **kwargs):
            return DummyResponseStream(
                [
                    SimpleNamespace(type="response.output_text.delta", delta="테스트 "),
                    SimpleNamespace(type="response.output_text.delta", delta="응답"),
                ],
                DummyResponse(),
            )


class DummyResponseStream:
    def __init__(self, events, final_response):
        self.events = events
        self.final_response = final_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        self._iter = iter(self.events)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def get_final_response(self):
        return self.final_response


class CaptureClient:
    def __init__(self):
        self.last_input = None

    class embeddings:
        @staticmethod
        async def create(*args, **kwargs):
            return DummyEmbeddingResponse()

    class responses:
        async def create(self, *args, **kwargs):
            return DummyResponse()

    @property
    def responses(self):
        class _Responses:
            def __init__(self, outer):
                self.outer = outer

            async def create(self, *args, **kwargs):
                self.outer.last_input = kwargs.get("input")
                return DummyResponse()

        return _Responses(self)


@pytest.mark.asyncio
async def test_chat_service_generate_uses_allowed_model():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepo()

    result = await service.generate(user_id=1, message="안녕", model="gpt-4.1-mini-2025-04-14")

    assert result.model == "gpt-4.1-mini-2025-04-14"
    assert result.answer == "테스트 응답"
    assert result.used_contexts == ["컨텍스트A", "컨텍스트B"]


def test_chat_service_rejects_disallowed_model():
    with pytest.raises(ValueError):
        ChatService._validate_model("gpt-4.5-preview-2025-02-27")


def test_build_system_prompt_discourages_unsolicited_context_for_simple_greetings():
    prompt = ChatService._build_system_prompt(
        DummyProfile(),
        ["이번주 금요일 오후 6시 시간 비워놔", "무슨 빵?"],
        "테스터의 아바타",
    )

    assert "짧게 인사만 하거나 가벼운 호응만 하면" in prompt
    assert "참고 컨텍스트를 먼저 꺼내지 마라" in prompt
    assert "사용자가 먼저 묻지 않은 일정, 취향, 과거 대화 내용을 갑자기 먼저 꺼내지 마라" in prompt


@pytest.mark.asyncio
async def test_chat_service_raises_when_profile_not_found():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepoNoProfile()

    with pytest.raises(ValueError, match="avatar profile not found"):
        await service.generate(user_id=999, message="안녕", model="gpt-4.1-mini-2025-04-14")


@pytest.mark.asyncio
async def test_chat_service_generates_with_empty_contexts():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepoNoContexts()

    result = await service.generate(user_id=1, message="안녕", model="gpt-4.1-mini-2025-04-14")

    assert result.answer == "테스트 응답"
    assert result.used_contexts == []


@pytest.mark.asyncio
async def test_chat_service_identity_question_uses_avatar_name():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepo()

    result = await service.generate(user_id=1, message="너 누구야?", model="gpt-4.1-mini-2025-04-14")

    assert result.answer == "나는 테스터의 아바타야."
    assert result.used_contexts == []


@pytest.mark.asyncio
async def test_chat_service_identity_question_fallback_name_when_nickname_missing():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepo()

    class ProfileNoNickname:
        nickname = None
        personality = "유쾌함"
        speech_style = "반말"
        profile_summary = "게임과 영화 좋아함"

    async def _no_nickname_profile(_user_id: int):
        return ProfileNoNickname()

    service.repo.get_profile_by_user_id = _no_nickname_profile

    result = await service.generate(user_id=1, message="이름이 뭐야?", model="gpt-4.1-mini-2025-04-14")

    assert result.answer == "나는 사용자의 아바타야."


@pytest.mark.asyncio
async def test_chat_service_includes_history_when_calling_openai():
    capture_client = CaptureClient()
    service = ChatService(session=None, client=capture_client)
    service.repo = DummyRepo()

    history = [
        type("HistoryItem", (), {"role": "USER", "content": "안녕"})(),
        type("HistoryItem", (), {"role": "AVATAR", "content": "반가워"})(),
    ]
    await service.generate(
        user_id=1,
        message="오늘 뭐해?",
        model="gpt-4.1-mini-2025-04-14",
        history=history,
    )

    assert capture_client.last_input is not None
    assert capture_client.last_input[1] == {"role": "user", "content": "안녕"}
    assert capture_client.last_input[2] == {"role": "assistant", "content": "반가워"}


@pytest.mark.asyncio
async def test_chat_service_stream_generate_emits_meta_delta_done():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepo()

    events = [
        event
        async for event in service.stream_generate(
            user_id=1,
            message="안녕",
            model="gpt-4.1-mini-2025-04-14",
        )
    ]

    assert [event.event for event in events] == ["meta", "delta", "delta", "done"]
    assert events[0].data["used_contexts"] == ["컨텍스트A", "컨텍스트B"]
    assert events[1].data == {"content": "테스트 "}
    assert events[2].data == {"content": "응답"}
    assert events[3].data["answer"] == "테스트 응답"


@pytest.mark.asyncio
async def test_chat_service_stream_generate_identity_question_finishes_without_openai():
    service = ChatService(session=None, client=DummyClient())
    service.repo = DummyRepo()

    events = [
        event
        async for event in service.stream_generate(
            user_id=1,
            message="너 누구야?",
            model="gpt-4.1-mini-2025-04-14",
        )
    ]

    assert [event.event for event in events] == ["meta", "delta", "done"]
    assert events[1].data == {"content": "나는 테스터의 아바타야."}
    assert events[2].data["answer"] == "나는 테스터의 아바타야."
