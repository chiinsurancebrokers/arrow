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


def _actual_days(trip: dict) -> int:
    try:
        return int(trip.get("days", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _pool_days(trip: dict) -> int:
    if _is_canceled(trip):
        return 0
    try:
        return int(trip.get("pool_charge_days", _actual_days(trip)) or 0)
    except (TypeError, ValueError):
        return 0


def _employee_row(employee: dict) -> dict:
    trips = employee.get("trips", []) or []
    active = [t for t in trips if not _is_canceled(t)]
    canceled = [t for t in trips if _is_canceled(t)]
    goodwill = [t for t in active if bool(t.get("goodwill_exception"))]
    pool_counted = [t for t in active if _pool_days(t) > 0]
    return {
        "name": employee.get("name", ""),
        "email": employee.get("email", ""),
        "days": sum(_pool_days(t) for t in trips),
        "travel_days": sum(_actual_days(t) for t in active),
        "trip_count": len(active),
        "pool_trip_count": len(pool_counted),
        "goodwill_exception_count": len(goodwill),
        "canceled_trip_count": len(canceled),
        "trips": trips,
    }


def tracker_summary() -> dict:
    data = current_data()
    employees = data.get("employees", []) or []
    rows = [_employee_row(e) for e in employees]

    total_days = sum(r["days"] for r in rows)
    total_trips = sum(r["trip_count"] for r in rows)
    goodwill = sum(r["goodwill_exception_count"] for r in rows)
    active_rows = [r for r in rows if r["trip_count"] > 0]
    limit = int(data.get("annual_day_limit", 250) or 250)

    return {
        "certificate_no": data.get("certificate_no"),
        "policy_year": data.get("policy_year"),
        "annual_day_limit": limit,
        "total_days": total_days,
        "days_remaining": max(limit - total_days, 0),
        "total_trips": total_trips,
        "goodwill_exception_count": goodwill,
        "employee_count": len(active_rows),
        "roster_count": len(employees),
        "employees": active_rows,
        "storage": storage_status(),
        "administrative_notice": (
            "The 2026/27 administrative pool began at 0/250 on renewal. Confirmed current-policy "
            "trips are preloaded and subsequent trips are maintained through CHI Admin. Pool charge "
            "days can differ from travel days only when CHI records an approved exception. Pending "
            "trips reserve their pool-charge days. The 250-day pool is an Arrow/CHI administrative "
            "tracking convention, not a benefit or limit stated in Certificate CGT P804302600."
        ),
    }


def archive_summary() -> dict:
    data = archived_trips()
    employees = data.get("employees", []) or []
    rows = [_employee_row(e) for e in employees]

    total_days = sum(r["days"] for r in rows)
    pool_trips = sum(r["pool_trip_count"] for r in rows)
    covered_trips = sum(r["trip_count"] for r in rows)
    goodwill = sum(r["goodwill_exception_count"] for r in rows)
    canceled_trips = sum(r["canceled_trip_count"] for r in rows)
    limit = int(data.get("annual_day_limit", 250) or 250)

    return {
        "certificate_no": data.get("certificate_no"),
        "policy_year": data.get("policy_year"),
        "annual_day_limit": limit,
        "total_days": total_days,
        "days_remaining_at_close": max(limit - total_days, 0),
        "trip_count": pool_trips,
        "covered_trip_count": covered_trips,
        "goodwill_exception_count": goodwill,
        "canceled_trip_count": canceled_trips,
        "employee_count": len(employees),
        "employees": rows,
        "archived": True,
        "notice": (
            "The previous 250-day administrative pool closed fully used at 250/250. "
            "Myrsini Andreou's 16–18 September 2026 Geneva trip was allocated as the final "
            "3-day deduction. Pierre Loth's 1–4 September 2026 Geneva trip is retained as a "
            "Pulse goodwill approval with zero additional pool charge. These historical allocations "
            "do not reduce the current 2026/27 pool."
        ),
    }


def tracker_context_for_hal() -> str:
    return json.dumps(tracker_summary(), ensure_ascii=False, indent=2)
