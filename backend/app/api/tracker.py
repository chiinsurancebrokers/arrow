from __future__ import annotations

from fastapi import APIRouter

from backend.app.knowledge.trip_facts import tracker_summary
from backend.app.knowledge.trip_store import current_data

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


@router.get("/current")
def current_tracker() -> dict:
    """Public current-policy data used by the existing authorised Arrow portal.

    Historical policy data are intentionally not returned here.
    """
    return {
        "summary": tracker_summary(),
        "current": current_data(),
    }
