"""Pins down the renewal reset: trips before 01/09/2026 must be archived
(not live-counted), and the archive must still add up to what was on the
certificate before the cutover."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "trips"


def _load(name):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def test_archive_has_30_employees_and_247_days():
    archive = _load("archive_2025-09_2026-08.json")
    assert archive["certificate_no"] == "CGT P804302500 CN"
    assert len(archive["employees"]) == 30
    assert archive["total_days_used"] == 247


def test_current_year_starts_reset():
    current = _load("current_2026-09_2027-08.json")
    assert current["certificate_no"] == "CGT P804302600"
    total_days = sum(
        t["days"]
        for e in current["employees"]
        for t in e["trips"]
        if not t.get("canceled")
    )
    # Only the one trip starting on/after 01/09/2026 should have carried over.
    assert total_days == 3


def test_no_trip_in_current_year_starts_before_cutoff():
    from datetime import datetime

    current = _load("current_2026-09_2027-08.json")
    cutoff = datetime(2026, 9, 1)
    for emp in current["employees"]:
        for trip in emp["trips"]:
            start = datetime.strptime(trip["dates"].split(" - ")[0].strip(), "%d/%m/%Y")
            assert start >= cutoff, f"{emp['name']}'s trip {trip} predates the renewal cutoff"
