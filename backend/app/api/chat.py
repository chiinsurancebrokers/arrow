from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.adviser import ask_hal

router = APIRouter()


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    try:
        reply = await ask_hal(
            payload.message,
            history=[turn.model_dump() for turn in payload.history],
        )
    except Exception as exc:  # noqa: BLE001 - surface a safe message, log the real one
        raise HTTPException(status_code=502, detail="HAL is temporarily unavailable.") from exc

    return ChatResponse(answer=reply.answer, citations=reply.citations)
