"""Renewal split tests.

The 2026/27 policy-year seed intentionally starts at literal zero. Current
trips are added through CHI Admin and stored in the runtime SQLite database.
"""
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


def test_current_year_seed_starts_literal_zero():
    current = _load("current_2026-09_2027-08.json")
    assert current["certificate_no"] == "CGT P804302600"
    assert len(current["employees"]) == 30
    assert sum(len(e.get("trips", [])) for e in current["employees"]) == 0
    total_days = sum(
        t["days"]
        for e in current["employees"]
        for t in e.get("trips", [])
        if not t.get("canceled")
    )
    assert total_days == 0
