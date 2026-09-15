from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.app.knowledge.trip_store import current_data, storage_status

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_PATH = ROOT / "data" / "trips" / "archive_2025-09_2026-08.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def archived_trips() -> dict:
    return _load(ARCHIVE_PATH)


def _is_canceled(trip: dict) -> bool:
    if bool(trip.get("canceled")):
        return True
    return str(trip.get("status", "")).strip().lower() in {
        "cancelled", "canceled", "cancel", "void"
    }


def _trip_days(trip: dict) -> int:
    if _is_canceled(trip):
        return 0
    try:
        return int(trip.get("days", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _employee_row(employee: dict) -> dict:
    trips = employee.get("trips", []) or []
    counted = [t for t in trips if not _is_canceled(t)]
    canceled = [t for t in trips if _is_canceled(t)]
    return {
        "name": employee.get("name", ""),
        "email": employee.get("email", ""),
        "days": sum(_trip_days(t) for t in trips),
        "trip_count": len(counted),
        "canceled_trip_count": len(canceled),
        "trips": trips,
    }


def tracker_summary() -> dict:
    data = current_data()
    employees = data.get("employees", []) or []
    rows = [_employee_row(e) for e in employees]

    total_days = sum(r["days"] for r in rows)
    total_trips = sum(r["trip_count"] for r in rows)
    active_rows = [r for r in rows if r["trip_count"] > 0]
    limit = int(data.get("annual_day_limit", 250) or 250)

    return {
        "certificate_no": data.get("certificate_no"),
        "policy_year": data.get("policy_year"),
        "annual_day_limit": limit,
        "total_days": total_days,
        "days_remaining": max(limit - total_days, 0),
        "total_trips": total_trips,
        "employee_count": len(active_rows),
        "roster_count": len(employees),
        "employees": active_rows,
        "storage": storage_status(),
        "administrative_notice": (
            "The 2026/27 tracker starts at zero. Only trips entered for the current "
            "policy year count against the 250-day Arrow/CHI administrative pool. "
            "Pending trips reserve their days. The 250-day pool is an administrative "
            "tracking convention, not a benefit or limit stated in Certificate CGT P804302600."
        ),
    }


def archive_summary() -> dict:
    data = archived_trips()
    employees = data.get("employees", []) or []
    rows = [_employee_row(e) for e in employees]

    total_days = sum(r["days"] for r in rows)
    counted_trips = sum(r["trip_count"] for r in rows)
    canceled_trips = sum(r["canceled_trip_count"] for r in rows)
    limit = int(data.get("annual_day_limit", 250) or 250)

    return {
        "certificate_no": data.get("certificate_no"),
        "policy_year": data.get("policy_year"),
        "annual_day_limit": limit,
        "total_days": total_days,
        "days_remaining_at_close": max(limit - total_days, 0),
        "trip_count": counted_trips,
        "canceled_trip_count": canceled_trips,
        "employee_count": len(employees),
        "employees": rows,
        "archived": True,
        "notice": (
            "Historical administrative record for the previous policy period. "
            "These trips do not count against the current 2026/27 pool."
        ),
    }


def tracker_context_for_hal() -> str:
    return json.dumps(tracker_summary(), ensure_ascii=False, indent=2)
