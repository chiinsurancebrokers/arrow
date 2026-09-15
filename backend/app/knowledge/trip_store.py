from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "data" / "trips" / "current_2026-09_2027-08.json"
DEFAULT_SQLITE_PATH = ROOT / "data" / "runtime" / "arrow_trips.sqlite3"

POLICY_START = date(2026, 9, 1)
POLICY_END = date(2027, 8, 31)
BASELINE_SEED_KEY = "current_2026_27_seed_v36"

metadata = MetaData()

employees_table = Table(
    "employees",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(180), nullable=False, unique=True),
    Column("email", String(240), nullable=False, server_default=""),
)

trips_table = Table(
    "trips",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("route", String(220), nullable=False),
    Column("days", Integer, nullable=False),
    Column("canceled", Boolean, nullable=False, server_default="false"),
    Column("notes", Text, nullable=False, server_default=""),
    Column("policy_allocation", String(20), nullable=False, server_default="current"),
    Column("pool_charge_days", Integer, nullable=False, server_default="0"),
    Column("goodwill_exception", Boolean, nullable=False, server_default="false"),
    Column("approval_note", Text, nullable=False, server_default=""),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

trip_audit_table = Table(
    "trip_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("action", String(40), nullable=False),
    Column("trip_id", String(64), nullable=True),
    Column("snapshot", Text, nullable=False),
)

app_meta_table = Table(
    "app_meta",
    metadata,
    Column("key", String(120), primary_key=True),
    Column("value", Text, nullable=False),
)


def _normalise_database_url(raw: str) -> str:
    value = raw.strip()
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


def _sqlite_url() -> str:
    configured = os.getenv("TRIP_DB_PATH", "").strip()
    path = Path(configured) if configured else DEFAULT_SQLITE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{path}"


def database_url() -> str:
    raw = os.getenv("DATABASE_URL", "").strip()
    return _normalise_database_url(raw) if raw else _sqlite_url()


@lru_cache(maxsize=8)
def _engine_for(url: str) -> Engine:
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, future=True, **kwargs)


def engine() -> Engine:
    return _engine_for(database_url())


def storage_status() -> dict:
    postgres = bool(os.getenv("DATABASE_URL", "").strip())
    if postgres:
        return {
            "backend": "postgresql",
            "production_ready": True,
            "configured": True,
            "location": "Railway PostgreSQL via DATABASE_URL",
            "warning": None,
        }
    configured_sqlite = bool(os.getenv("TRIP_DB_PATH", "").strip())
    return {
        "backend": "sqlite-local-fallback",
        "production_ready": False,
        "configured": configured_sqlite,
        "location": str(Path(os.getenv("TRIP_DB_PATH", "").strip()) if configured_sqlite else DEFAULT_SQLITE_PATH),
        "warning": (
            "DATABASE_URL is not configured. The app is using the local SQLite fallback. "
            "This is suitable for local testing only; production trip writes should use Railway PostgreSQL."
        ),
    }


def _migrate_v35_schema(eng: Engine) -> None:
    """Add v3.6 allocation fields to an existing v3.5 trips table.

    create_all() creates these columns for new databases but does not ALTER
    existing tables, so this lightweight migration is intentionally idempotent.
    """
    inspector = inspect(eng)
    if "trips" not in inspector.get_table_names():
        return

    cols = {c["name"] for c in inspector.get_columns("trips")}
    statements = []
    if "policy_allocation" not in cols:
        statements.append("ALTER TABLE trips ADD COLUMN policy_allocation VARCHAR(20) NOT NULL DEFAULT 'current'")
    if "pool_charge_days" not in cols:
        statements.append("ALTER TABLE trips ADD COLUMN pool_charge_days INTEGER")
    if "goodwill_exception" not in cols:
        statements.append("ALTER TABLE trips ADD COLUMN goodwill_exception BOOLEAN NOT NULL DEFAULT FALSE")
    if "approval_note" not in cols:
        statements.append("ALTER TABLE trips ADD COLUMN approval_note TEXT NOT NULL DEFAULT ''")

    with eng.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
        conn.execute(text("UPDATE trips SET pool_charge_days = days WHERE pool_charge_days IS NULL"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc


def _parse_baseline_dates(trip: dict) -> tuple[date, date]:
    if trip.get("start_date") and trip.get("end_date"):
        return _parse_date(str(trip["start_date"])), _parse_date(str(trip["end_date"]))
    start_text, end_text = [part.strip() for part in str(trip.get("dates", "")).split(" - ", 1)]
    return (
        datetime.strptime(start_text, "%d/%m/%Y").date(),
        datetime.strptime(end_text, "%d/%m/%Y").date(),
    )


def _validate_dates(start_date: str, end_date: str) -> tuple[date, date]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if end < start:
        raise ValueError("End date cannot be before start date.")
    if start < POLICY_START or start > POLICY_END:
        raise ValueError(
            f"Trip start must fall within the current policy year "
            f"({POLICY_START.isoformat()} to {POLICY_END.isoformat()})."
        )
    return start, end


def _normalise_route(route: str) -> str:
    value = "-".join(part.strip().upper() for part in str(route).split("-") if part.strip())
    if len(value) < 3:
        raise ValueError("Please enter a route, for example ATH-GVA-ATH.")
    return value


def _days(start: date, end: date) -> int:
    return (end - start).days + 1


def _pool_charge(actual_days: int, requested: int | None, goodwill_exception: bool) -> int:
    if requested is None:
        return 0 if goodwill_exception else actual_days
    value = int(requested)
    if value < 0:
        raise ValueError("Pool charge days cannot be negative.")
    if value > actual_days:
        raise ValueError("Pool charge days cannot exceed the actual trip duration.")
    return value


def _trip_select():
    return (
        select(
            trips_table,
            employees_table.c.name.label("employee"),
            employees_table.c.email.label("email"),
        )
        .select_from(trips_table.join(employees_table, employees_table.c.id == trips_table.c.employee_id))
    )


def _row_to_trip(row) -> dict:
    start = row["start_date"]
    end = row["end_date"]
    created = row["created_at"]
    updated = row["updated_at"]
    return {
        "id": row["id"],
        "employee": row["employee"],
        "email": row["email"] or "",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "dates": f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}",
        "route": row["route"],
        "days": int(row["days"]),
        "canceled": bool(row["canceled"]),
        "notes": row["notes"] or "",
        "policy_allocation": row["policy_allocation"] or "current",
        "pool_charge_days": int(row["pool_charge_days"] if row["pool_charge_days"] is not None else row["days"]),
        "goodwill_exception": bool(row["goodwill_exception"]),
        "approval_note": row["approval_note"] or "",
        "created_at": created.isoformat() if created else None,
        "updated_at": updated.isoformat() if updated else None,
    }


def _audit(conn, action: str, trip_id: str | None, snapshot: dict) -> None:
    conn.execute(
        insert(trip_audit_table).values(
            timestamp=_utc_now(),
            action=action,
            trip_id=trip_id,
            snapshot=json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str),
        )
    )


def _employee_id(conn, name: str, email: str = "") -> int:
    clean = str(name).strip()
    if not clean:
        raise ValueError("Employee name is required.")

    row = conn.execute(
        select(employees_table.c.id, employees_table.c.email)
        .where(func.lower(employees_table.c.name) == clean.lower())
    ).mappings().first()

    if row:
        if email and email.strip() != (row["email"] or ""):
            conn.execute(
                update(employees_table)
                .where(employees_table.c.id == row["id"])
                .values(email=email.strip())
            )
        return int(row["id"])

    result = conn.execute(
        insert(employees_table).values(name=clean, email=email.strip()).returning(employees_table.c.id)
    )
    return int(result.scalar_one())


def _ensure_schema_roster_and_seed() -> None:
    eng = engine()
    metadata.create_all(eng)
    _migrate_v35_schema(eng)

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    with eng.begin() as conn:
        # Ensure the full employee roster exists even in an already-created DB.
        for employee in baseline.get("employees", []):
            name = str(employee.get("name", "")).strip()
            if not name:
                continue
            existing = conn.execute(
                select(employees_table.c.id)
                .where(func.lower(employees_table.c.name) == name.lower())
            ).first()
            if not existing:
                conn.execute(insert(employees_table).values(
                    name=name, email=str(employee.get("email", "")).strip()
                ))

        seeded = conn.execute(
            select(app_meta_table.c.value).where(app_meta_table.c.key == BASELINE_SEED_KEY)
        ).scalar_one_or_none()
        if seeded:
            return

        # One-time idempotent seed of the confirmed 2026/27 renewal trips.
        now = _utc_now()
        for employee in baseline.get("employees", []):
            name = str(employee.get("name", "")).strip()
            for trip in employee.get("trips", []) or []:
                start, end = _parse_baseline_dates(trip)
                route = _normalise_route(str(trip.get("route", "")))
                employee_id = _employee_id(conn, name, str(employee.get("email", "")))
                exists = conn.execute(
                    select(trips_table.c.id)
                    .where(trips_table.c.employee_id == employee_id)
                    .where(trips_table.c.start_date == start)
                    .where(trips_table.c.end_date == end)
                    .where(trips_table.c.route == route)
                ).scalar_one_or_none()
                if exists:
                    continue

                actual = int(trip.get("days") or _days(start, end))
                charge = int(trip.get("pool_charge_days", actual))
                seed_id = "seed-" + uuid.uuid5(
                    uuid.NAMESPACE_URL, f"{name}|{start.isoformat()}|{end.isoformat()}|{route}"
                ).hex
                conn.execute(insert(trips_table).values(
                    id=seed_id,
                    employee_id=employee_id,
                    start_date=start,
                    end_date=end,
                    route=route,
                    days=actual,
                    canceled=bool(trip.get("canceled", False)),
                    notes=str(trip.get("notes", "")).strip(),
                    policy_allocation=str(trip.get("policy_allocation", "current")),
                    pool_charge_days=charge,
                    goodwill_exception=bool(trip.get("goodwill_exception", False)),
                    approval_note=str(trip.get("approval_note", "")).strip(),
                    created_at=now,
                    updated_at=now,
                ))
                _audit(conn, "seed", seed_id, {
                    "employee": name,
                    "dates": f"{start.isoformat()} to {end.isoformat()}",
                    "route": route,
                    "days": actual,
                    "pool_charge_days": charge,
                })

        conn.execute(insert(app_meta_table).values(key=BASELINE_SEED_KEY, value=now.isoformat()))


def roster() -> list[dict]:
    _ensure_schema_roster_and_seed()
    with engine().connect() as conn:
        rows = conn.execute(
            select(employees_table.c.id, employees_table.c.name, employees_table.c.email)
            .order_by(employees_table.c.name)
        ).mappings().all()
        return [dict(r) for r in rows]


def list_trips() -> list[dict]:
    _ensure_schema_roster_and_seed()
    with engine().connect() as conn:
        rows = conn.execute(
            _trip_select().order_by(trips_table.c.start_date.desc(), employees_table.c.name)
        ).mappings().all()
        return [_row_to_trip(r) for r in rows]


def current_data() -> dict:
    people = roster()
    by_name = {
        e["name"]: {"name": e["name"], "email": e["email"], "trips": []}
        for e in people
    }
    for trip in list_trips():
        by_name.setdefault(
            trip["employee"],
            {"name": trip["employee"], "email": trip.get("email", ""), "trips": []},
        )["trips"].append(
            {
                "id": trip["id"],
                "days": trip["days"],
                "pool_charge_days": trip["pool_charge_days"],
                "dates": trip["dates"],
                "start_date": trip["start_date"],
                "end_date": trip["end_date"],
                "route": trip["route"],
                "canceled": trip["canceled"],
                "notes": trip["notes"],
                "policy_allocation": trip["policy_allocation"],
                "goodwill_exception": trip["goodwill_exception"],
                "approval_note": trip["approval_note"],
            }
        )
    return {
        "certificate_no": "CGT P804302600",
        "policy_year": "2026-09-01 to 2027-08-31",
        "annual_day_limit": 250,
        "employees": list(by_name.values()),
    }


def add_trip(
    *, employee: str, start_date: str, end_date: str, route: str,
    email: str = "", notes: str = "", pool_charge_days: int | None = None,
    goodwill_exception: bool = False, approval_note: str = "",
) -> dict:
    _ensure_schema_roster_and_seed()
    start, end = _validate_dates(start_date, end_date)
    clean_route = _normalise_route(route)
    actual = _days(start, end)
    charge = _pool_charge(actual, pool_charge_days, goodwill_exception)
    trip_id = uuid.uuid4().hex
    now = _utc_now()

    with engine().begin() as conn:
        employee_id = _employee_id(conn, employee, email)
        conn.execute(
            insert(trips_table).values(
                id=trip_id,
                employee_id=employee_id,
                start_date=start,
                end_date=end,
                route=clean_route,
                days=actual,
                canceled=False,
                notes=notes.strip(),
                policy_allocation="current",
                pool_charge_days=charge,
                goodwill_exception=bool(goodwill_exception),
                approval_note=approval_note.strip(),
                created_at=now,
                updated_at=now,
            )
        )
        row = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        result = _row_to_trip(row)
        _audit(conn, "create", trip_id, result)
        return result


def update_trip(
    trip_id: str, *, employee: str, start_date: str, end_date: str, route: str,
    email: str = "", notes: str = "", pool_charge_days: int | None = None,
    goodwill_exception: bool = False, approval_note: str = "",
) -> dict:
    _ensure_schema_roster_and_seed()
    start, end = _validate_dates(start_date, end_date)
    clean_route = _normalise_route(route)
    actual = _days(start, end)
    charge = _pool_charge(actual, pool_charge_days, goodwill_exception)

    with engine().begin() as conn:
        existing = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        if not existing:
            raise KeyError("Trip not found.")
        before = _row_to_trip(existing)
        employee_id = _employee_id(conn, employee, email)

        conn.execute(
            update(trips_table)
            .where(trips_table.c.id == trip_id)
            .values(
                employee_id=employee_id,
                start_date=start,
                end_date=end,
                route=clean_route,
                days=actual,
                notes=notes.strip(),
                pool_charge_days=charge,
                goodwill_exception=bool(goodwill_exception),
                approval_note=approval_note.strip(),
                updated_at=_utc_now(),
            )
        )
        row = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        after = _row_to_trip(row)
        _audit(conn, "update", trip_id, {"before": before, "after": after})
        return after


def set_canceled(trip_id: str, canceled: bool) -> dict:
    _ensure_schema_roster_and_seed()
    with engine().begin() as conn:
        row = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        if not row:
            raise KeyError("Trip not found.")
        before = _row_to_trip(row)
        conn.execute(
            update(trips_table)
            .where(trips_table.c.id == trip_id)
            .values(canceled=bool(canceled), updated_at=_utc_now())
        )
        row = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        after = _row_to_trip(row)
        _audit(conn, "cancel" if canceled else "restore", trip_id, {"before": before, "after": after})
        return after


def delete_trip(trip_id: str) -> None:
    _ensure_schema_roster_and_seed()
    with engine().begin() as conn:
        row = conn.execute(_trip_select().where(trips_table.c.id == trip_id)).mappings().first()
        if not row:
            raise KeyError("Trip not found.")
        before = _row_to_trip(row)
        _audit(conn, "delete", trip_id, before)
        conn.execute(delete(trips_table).where(trips_table.c.id == trip_id))
