from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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


@router.post("/stream")
async def chat_stream(request: ChatRequest, session: DbSessionDep) -> StreamingResponse:
    service = ChatService(session)

    async def event_generator():
        try:
            async for event in service.stream_generate(
                user_id=request.user_id,
                message=request.message,
                history=request.history,
            ):
                yield _format_sse(event.event, event.data)
        except ValueError as exc:
            yield _format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
