from __future__ import annotations

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
