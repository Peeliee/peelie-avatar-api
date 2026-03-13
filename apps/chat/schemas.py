from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: Literal["USER", "AVATAR"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    user_id: int
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    user_id: int
    model: str
    answer: str
    used_contexts: list[str]
