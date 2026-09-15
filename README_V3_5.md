# Arrow v3.5 — Railway PostgreSQL trip administration

This package is cumulative: it includes the v3.4 CHI trip editor, literal
0 / 0 / 250 renewal reset, restricted-destination alerts, Arrow read-only
history, and HAL expand/thinking feedback.

## Production database

Production current-policy trips now use Railway PostgreSQL through `DATABASE_URL`.
The app automatically creates these tables on first connection:

- `employees`
- `trips`
- `trip_audit`

No manual SQL setup or migration command is required for this first version.

The committed JSON file is used only to seed the employee roster. It contains
zero current-policy trips, so a new database starts exactly at:

- 0 travelling employees
- 0 days reserved/used
- 250 days remaining

## Railway variable

Create a Railway PostgreSQL service in the same project, then add this variable
to the Arrow app service:

    DATABASE_URL=${{Postgres.DATABASE_URL}}

Use a Railway reference variable rather than copying the password/URL manually.
The database can remain private; the app and Postgres communicate inside the
Railway project.

## Local testing

If `DATABASE_URL` is absent, v3.5 keeps a SQLite fallback for local tests only.
You may optionally set:

    TRIP_DB_PATH=/some/local/path/arrow_trips.sqlite3

CHI Admin will clearly report that the SQLite fallback is not production-ready.

## Apply

From the Arrow repo root:

    git switch main
    git pull --ff-only origin main
    git switch -c arrow-v3.5-postgres
    unzip -o ../arrow-v3.5-postgres.zip
    python tools/apply_v35.py
    python -m pip install -r requirements-dev.txt
    pytest -q
    git diff --check

Do not push until the diff/tests have been reviewed.
