from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.chat import ChatTurn
from backend.app.knowledge.policy_facts import certificate_summary, load_policy_facts
from backend.app.knowledge.trip_facts import archive_summary, tracker_context_for_hal, tracker_summary
from backend.app.knowledge.trip_store import (
    add_trip,
    delete_trip,
    list_trips,
    roster,
    set_canceled,
    storage_status,
    update_trip,
)
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


def _require_chi(key: str | None) -> None:
    if _role_from_key(key) != "chi":
        raise HTTPException(status_code=403, detail="CHI administrator access required")


class AdminChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class TripInput(BaseModel):
    employee: str = Field(..., min_length=1, max_length=160)
    email: str = Field(default="", max_length=200)
    start_date: str = Field(..., min_length=10, max_length=10)
    end_date: str = Field(..., min_length=10, max_length=10)
    route: str = Field(..., min_length=3, max_length=200)
    notes: str = Field(default="", max_length=1000)


class CancelInput(BaseModel):
    canceled: bool


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

    # Arrow sees current tracker read-only. CHI also sees it because CHI is the
    # write/control role for current trips.
    if role in {"arrow", "chi"}:
        result["tracker"] = tracker_summary()

    # Previous policy history remains Arrow-admin information.
    if role == "arrow":
        result["archive"] = archive_summary()

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
        result["trip_management"] = {
            "storage": storage_status(),
            "roster": roster(),
            "trips": list_trips(),
        }
    return result


@router.get("/trips")
def get_trips(x_admin_key: str | None = Header(default=None)) -> dict:
    _require_chi(x_admin_key)
    return {
        "summary": tracker_summary(),
        "storage": storage_status(),
        "roster": roster(),
        "trips": list_trips(),
    }


@router.post("/trips")
def create_trip(payload: TripInput, x_admin_key: str | None = Header(default=None)) -> dict:
    _require_chi(x_admin_key)
    try:
        trip = add_trip(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"trip": trip, "summary": tracker_summary()}


@router.put("/trips/{trip_id}")
def edit_trip(trip_id: str, payload: TripInput, x_admin_key: str | None = Header(default=None)) -> dict:
    _require_chi(x_admin_key)
    try:
        trip = update_trip(trip_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"trip": trip, "summary": tracker_summary()}


@router.post("/trips/{trip_id}/cancel")
def cancel_trip(trip_id: str, payload: CancelInput, x_admin_key: str | None = Header(default=None)) -> dict:
    _require_chi(x_admin_key)
    try:
        trip = set_canceled(trip_id, payload.canceled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"trip": trip, "summary": tracker_summary()}


@router.delete("/trips/{trip_id}")
def remove_trip(trip_id: str, x_admin_key: str | None = Header(default=None)) -> dict:
    _require_chi(x_admin_key)
    try:
        delete_trip(trip_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": trip_id, "summary": tracker_summary()}


@router.post("/chat")
async def admin_chat(payload: AdminChatRequest, x_admin_key: str | None = Header(default=None)) -> dict:
    role = _role_from_key(x_admin_key)
    reply = await ask_hal(
        payload.message,
        history=[turn.model_dump() for turn in payload.history],
        tracker_context=tracker_context_for_hal() if role == "arrow" else None,
    )
    return {**reply.__dict__, "admin_role": role}
