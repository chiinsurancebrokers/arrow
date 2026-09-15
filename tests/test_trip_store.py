import pytest

from backend.app.knowledge import trip_store
from backend.app.knowledge.trip_facts import tracker_summary


def _db(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    path = tmp_path / "trips.sqlite3"
    monkeypatch.setenv("TRIP_DB_PATH", str(path))
    return path


def test_current_seed_is_23_days_227_remaining(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    summary = tracker_summary()
    assert summary["employee_count"] == 4
    assert summary["total_trips"] == 4
    assert summary["total_days"] == 23
    assert summary["days_remaining"] == 227
    assert summary["roster_count"] == 30


def test_standard_trip_defaults_pool_charge_to_actual_days(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    before = tracker_summary()
    trip = trip_store.add_trip(
        employee="MYRSINI ANDREOU",
        start_date="2026-12-01",
        end_date="2026-12-03",
        route="ATH-GVA-ATH",
    )
    assert trip["days"] == 3
    assert trip["pool_charge_days"] == 3
    after = tracker_summary()
    assert after["total_days"] == before["total_days"] + 3


def test_goodwill_trip_can_have_zero_pool_charge(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    before = tracker_summary()
    trip = trip_store.add_trip(
        employee="PIERRE LOTH",
        start_date="2026-12-10",
        end_date="2026-12-13",
        route="ATH-GVA-ATH",
        goodwill_exception=True,
        approval_note="Test goodwill approval",
    )
    assert trip["days"] == 4
    assert trip["pool_charge_days"] == 0
    assert trip["goodwill_exception"] is True
    after = tracker_summary()
    assert after["total_days"] == before["total_days"]
    assert after["total_trips"] == before["total_trips"] + 1


def test_pool_override_cannot_exceed_trip_duration(tmp_path, monkeypatch):
    _db(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        trip_store.add_trip(
            employee="PIERRE LOTH",
            start_date="2026-12-10",
            end_date="2026-12-13",
            route="ATH-GVA-ATH",
            pool_charge_days=5,
        )


def test_postgres_is_production_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")
    status = trip_store.storage_status()
    assert status["backend"] == "postgresql"
    assert status["production_ready"] is True
    assert trip_store.database_url().startswith("postgresql+psycopg://")
