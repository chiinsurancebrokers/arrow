from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CURRENT_PATH = ROOT / "data" / "trips" / "current_2026-09_2027-08.json"
ARCHIVE_PATH = ROOT / "data" / "trips" / "archive_2025-09_2026-08.json"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def current_trips() -> dict:
    return _load(CURRENT_PATH)


@lru_cache(maxsize=1)
def archived_trips() -> dict:
    return _load(ARCHIVE_PATH)


def _trip_days(trip: dict) -> int:
    if str(trip.get("status", "")).lower() in {"cancelled", "canceled"}:
        return 0
    try:
        return int(trip.get("days", 0) or 0)
    except (TypeError, ValueError):
        return 0


def tracker_summary() -> dict:
    data = current_trips()
    employees = data.get("employees", [])
    employee_rows = []
    total_days = 0
    total_trips = 0

    for employee in employees:
        trips = employee.get("trips", []) or []
        days = sum(_trip_days(t) for t in trips)
        total_days += days
        total_trips += len(trips)
        employee_rows.append({
            "name": employee.get("name", ""),
            "email": employee.get("email", ""),
            "days": days,
            "trip_count": len(trips),
            "trips": trips,
        })

    limit = int(data.get("annual_day_limit", 250) or 250)
    return {
        "certificate_no": data.get("certificate_no"),
        "policy_year": data.get("policy_year"),
        "annual_day_limit": limit,
        "total_days": total_days,
        "days_remaining": max(limit - total_days, 0),
        "total_trips": total_trips,
        "employee_count": len(employees),
        "employees": employee_rows,
        "administrative_notice": (
            "The shared day pool is an Arrow/CHI administrative tracking convention, "
            "not a benefit or limit stated in Certificate CGT P804302600."
        ),
    }


def tracker_context_for_hal() -> str:
    return json.dumps(tracker_summary(), ensure_ascii=False, indent=2)
