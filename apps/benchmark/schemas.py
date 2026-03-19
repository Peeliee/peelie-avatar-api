from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BenchmarkOnboardingAnswer(BaseModel):
    question_id: int
    purpose: str
    answer: str
    option_tag: str | None = None


class BenchmarkAvatarIngestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    user_id: int
    nickname: str | None = None
    occurred_at: str | None = None
    answers: list[BenchmarkOnboardingAnswer]


class BenchmarkAvatarIngestResponse(BaseModel):
    event_id: str
    user_id: int
    created: bool

