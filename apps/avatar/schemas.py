from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OnboardingAnswer(BaseModel):
    question_id: int
    purpose: str
    answer: str
    option_tag: str | None = None


class OnboardingCompletedPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    user_id: int
    nickname: str | None = None
    occurred_at: str | None = None
    answers: list[OnboardingAnswer]


class AvatarChunk(BaseModel):
    category: str
    content: str
