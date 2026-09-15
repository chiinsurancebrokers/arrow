import json
from pathlib import Path

from backend.app.knowledge.trip_facts import archive_summary

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "trips"


def _load(name):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def test_archive_closes_exactly_at_250_with_goodwill_separate():
    archive = archive_summary()
    assert archive["certificate_no"] == "CGT P804302500 CN"
    assert archive["total_days"] == 250
    assert archive["days_remaining_at_close"] == 0
    assert archive["trip_count"] == 57
    assert archive["goodwill_exception_count"] == 1
    assert archive["canceled_trip_count"] == 6
    assert archive["employee_count"] == 30


def test_myrsini_final_trip_and_pierre_goodwill_are_recorded():
    data = _load("archive_2025-09_2026-08.json")
    by_name = {e["name"]: e for e in data["employees"]}

    myrsini = next(t for t in by_name["MYRSINI ANDREOU"]["trips"] if t["dates"] == "16/09/2026 - 18/09/2026")
    assert myrsini["pool_charge_days"] == 3
    assert myrsini["final_pool_trip"] is True

    pierre = next(t for t in by_name["PIERRE LOTH"]["trips"] if t["dates"] == "01/09/2026 - 04/09/2026")
    assert pierre["days"] == 4
    assert pierre["pool_charge_days"] == 0
    assert pierre["goodwill_exception"] is True


def test_current_seed_has_four_confirmed_trips_23_days():
    current = _load("current_2026-09_2027-08.json")
    trips = [
        (e["name"], t)
        for e in current["employees"]
        for t in e.get("trips", [])
        if not t.get("canceled")
    ]
    assert len(trips) == 4
    assert sum(t.get("pool_charge_days", t["days"]) for _, t in trips) == 23
    assert {name for name, _ in trips} == {
        "KOSTOPOULOS KONSTANTINOS",
        "MAXIMILLIAN KATSAROS",
        "ODYSSEAS RENIERIS",
        "CONSTANTINE MARK HADJIPATERAS",
    }
