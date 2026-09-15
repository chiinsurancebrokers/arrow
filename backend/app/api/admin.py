from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.chat import ChatTurn
from backend.app.knowledge.policy_facts import certificate_summary, load_policy_facts
from backend.app.knowledge.trip_facts import tracker_context_for_hal, tracker_summary
from backend.app.knowledge.full_policy import full_wording_available
from backend.app.services.adviser import ask_hal
from backend.app.services.rate_limit import usage_snapshot

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _role_from_key(key: str | None) -> str:
    if not key:
        raise HTTPException(status_code=401, detail="Administrator key required")
    chi = os.getenv("CHI_ADMIN_KEY", "")
    arrow = os.getenv("ARROW_ADMIN_KEY", "")
    if chi and secrets.compare_digest(key, chi):
        return "chi"
    if arrow and secrets.compare_digest(key, arrow):
        return "arrow"
    raise HTTPException(status_code=403, detail="Invalid administrator key")


class AdminChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


@router.get("/dashboard")
def dashboard(x_admin_key: str | None = Header(default=None)) -> dict:
    role = _role_from_key(x_admin_key)
    facts = load_policy_facts()
    claims = facts["claims_process"]
    result = {
        "role": role,
        "certificate": certificate_summary(),
        "claims_contacts": {
            "crawford_phone": claims["crawford_phone"],
            "crawford_email": claims["crawford_email"],
            "medical": claims["medical_emergency_helpline"],
            "kidnap_security": claims["kidnap_response"],
        },
    }
    if role == "arrow":
        result["tracker"] = tracker_summary()
    if role == "chi":
        result["provider_status"] = {
            "claude_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
            "openai_fallback_configured": bool(os.getenv("OPENAI_API_KEY")),
            "claude_model": os.getenv("HAL_MODEL", "claude-sonnet-4-6"),
            "openai_model": os.getenv("HAL_OPENAI_MODEL", "gpt-5.6-luna"),
            "full_wording_available": full_wording_available(),
            "employee_usage_guard": usage_snapshot(),
        }
        result["policy_admin"] = {
            "age_limit": facts.get("age_limit"),
            "law_and_jurisdiction": facts.get("law_and_jurisdiction"),
            "not_in_this_document": facts.get("not_in_this_document"),
        }
    return result


@router.post("/chat")
async def admin_chat(payload: AdminChatRequest, x_admin_key: str | None = Header(default=None)) -> dict:
    role = _role_from_key(x_admin_key)
    reply = await ask_hal(
        payload.message,
        history=[turn.model_dump() for turn in payload.history],
        tracker_context=tracker_context_for_hal() if role == "arrow" else None,
    )
    return {**reply.__dict__, "admin_role": role}
