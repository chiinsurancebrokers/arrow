from pathlib import Path

import pytest

from backend.app.knowledge import trip_store
from backend.app.knowledge.trip_facts import tracker_summary


def test_runtime_trip_store_starts_zero_and_counts_new_trip(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = tmp_path / "trips.sqlite3"
    monkeypatch.setenv("TRIP_DB_PATH", str(db))

    summary = tracker_summary()
    assert summary["employee_count"] == 0
    assert summary["total_days"] == 0
    assert summary["days_remaining"] == 250
    assert summary["roster_count"] == 30

    trip = trip_store.add_trip(
        employee="MYRSINI ANDREOU",
        start_date="2026-09-16",
        end_date="2026-09-18",
        route="ATH-GVA-ATH",
    )
    assert trip["days"] == 3

    summary = tracker_summary()
    assert summary["employee_count"] == 1
    assert summary["total_days"] == 3
    assert summary["days_remaining"] == 247

    trip_store.set_canceled(trip["id"], True)
    summary = tracker_summary()
    assert summary["employee_count"] == 0
    assert summary["total_days"] == 0
    assert summary["days_remaining"] == 250

    trip_store.delete_trip(trip["id"])
    assert trip_store.list_trips() == []


def test_trip_store_rejects_wrong_policy_year(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TRIP_DB_PATH", str(tmp_path / "trips.sqlite3"))
    with pytest.raises(ValueError):
        trip_store.add_trip(
            employee="MYRSINI ANDREOU",
            start_date="2026-08-31",
            end_date="2026-09-02",
            route="ATH-GVA-ATH",
        )


def test_postgres_is_the_production_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")
    status = trip_store.storage_status()
    assert status["backend"] == "postgresql"
    assert status["production_ready"] is True
    assert trip_store.database_url().startswith("postgresql+psycopg://")


def test_sqlite_fallback_is_not_marked_production_ready(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TRIP_DB_PATH", str(tmp_path / "local.sqlite3"))
    status = trip_store.storage_status()
    assert status["backend"] == "sqlite-local-fallback"
    assert status["production_ready"] is False
