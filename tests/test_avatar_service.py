import json

from apps.avatar.models import AvatarCategory
from apps.avatar.schemas import OnboardingCompletedPayload
from apps.avatar.service import AvatarIngestService, build_payload_from_stream


def test_build_payload_from_stream_parses_answers_json():
    fields = {
        "event_id": "event_123",
        "user_id": "42",
        "nickname": "테스터",
        "event_type": "onboarding.completed",
        "occurred_at": "2026-03-10T12:34:56",
        "answers_json": json.dumps(
            {
                "answers": [
                    {
                        "question_id": 1,
                        "purpose": "PERSONALITY_CONVERSATION_STYLE",
                        "answer": "무슨 빵?",
                        "option_tag": "FACT_FIRST",
                    },
                    {
                        "question_id": 2,
                        "purpose": "ETC_PURPOSE",
                        "answer": "아무거나",
                        "option_tag": None,
                    },
                ]
            }
        ),
    }

    event = build_payload_from_stream(fields)

    assert event.event_id == "event_123"
    assert event.user_id == 42
    assert len(event.answers) == 2
    assert event.answers[0].purpose == "PERSONALITY_CONVERSATION_STYLE"


def test_build_chunks_groups_other_bucket():
    event = OnboardingCompletedPayload.model_validate(
        {
            "event_id": "event_123",
            "user_id": 1,
            "answers": [
                {
                    "question_id": 1,
                    "purpose": "PERSONALITY_CONVERSATION_STYLE",
                    "answer": "무슨 빵?",
                    "option_tag": "FACT_FIRST",
                },
                {
                    "question_id": 2,
                    "purpose": "USER_INTERESTS",
                    "answer": "제이팝",
                    "option_tag": None,
                },
                {
                    "question_id": 3,
                    "purpose": "UNCLASSIFIED",
                    "answer": "기타 답변",
                    "option_tag": None,
                },
            ],
        }
    )

    service = AvatarIngestService(session=None)  # type: ignore[arg-type]
    chunks = service._build_chunks(event)
    categories = {chunk.category for chunk in chunks}

    assert AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value in categories
    assert AvatarCategory.USER_INTERESTS.value in categories
    assert AvatarCategory.OTHER.value in categories

    personality_chunk = next(
        chunk for chunk in chunks if chunk.category == AvatarCategory.PERSONALITY_CONVERSATION_STYLE.value
    )
    assert "FACT_FIRST" in personality_chunk.content


def test_extract_style_fields_and_summary():
    event = OnboardingCompletedPayload.model_validate(
        {
            "event_id": "event_abc",
            "user_id": 10,
            "answers": [
                {
                    "question_id": 1,
                    "purpose": "PERSONALITY_CONVERSATION_STYLE",
                    "answer": "무슨 일 있어?",
                    "option_tag": "감정, 사람에 먼저 반응하는 대화스타일",
                },
                {
                    "question_id": 2,
                    "purpose": "PERSONALITY_CONVERSATION_STYLE",
                    "answer": "편한 날 있니?",
                    "option_tag": "배려형",
                },
                {
                    "question_id": 3,
                    "purpose": "USER_INTERESTS",
                    "answer": "러닝에 빠져있음",
                    "option_tag": None,
                },
                {
                    "question_id": 5,
                    "purpose": "USER_INFO",
                    "answer": "주말 집콕",
                    "option_tag": None,
                },
            ],
        }
    )

    service = AvatarIngestService(session=None)  # type: ignore[arg-type]
    speech_style, personality = service._extract_style_fields(event.answers)
    summary = service._build_profile_summary(event.answers)

    assert speech_style == "감정, 사람에 먼저 반응하는 대화스타일"
    assert personality == "배려형"
    assert summary == "러닝에 빠져있음\n주말 집콕"
