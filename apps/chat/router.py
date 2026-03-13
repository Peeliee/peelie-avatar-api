from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.chat.schemas import ChatRequest, ChatResponse
from apps.chat.service import ChatService
from core.db import DbSessionDep

router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, session: DbSessionDep) -> ChatResponse:
    service = ChatService(session)
    try:
        result = await service.generate(
            user_id=request.user_id,
            message=request.message,
            history=request.history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ChatResponse(
        user_id=request.user_id,
        model=result.model,
        answer=result.answer,
        used_contexts=result.used_contexts,
    )
