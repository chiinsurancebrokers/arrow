# Railway PostgreSQL — step-by-step for Arrow v3.5

## What changes

- GitHub stores code and the zero-trip employee roster seed.
- Railway PostgreSQL stores live current-policy trip records.
- CHI Administrator can add/edit/cancel/delete trips.
- Arrow Administrator remains read-only.
- A fresh Postgres database starts at 0 travelling employees / 0 days / 250 remaining.

## Phase A — update the code locally

From the Arrow repository:

    cd ~/Downloads/arrow-travel-portal
    git switch main
    git pull --ff-only origin main
    git switch -c arrow-v3.5-postgres
    unzip -o ../arrow-v3.5-postgres.zip
    python tools/apply_v35.py
    python -m pip install -r requirements-dev.txt
    pytest -q
    git status
    git diff --stat
    git diff --check

Review before commit/push.

## Phase B — create PostgreSQL in Railway

1. Open the existing Railway project that contains the `arrow` service.
2. On the project canvas click `+ New`.
3. Choose `Database` -> `PostgreSQL`.
4. Wait until the Postgres service shows as deployed/healthy.
5. If Railway names it something other than `Postgres`, either rename it to `Postgres` or use its actual service name in the reference variable below.

Do not enable Public Access for this database. The Arrow application can reach it through Railway's private project network.

## Phase C — connect Arrow to Postgres

1. Click the existing `arrow` application service (not the Postgres service).
2. Open `Variables`.
3. Click `New Variable`, or use `Raw Editor`.
4. Add:

       DATABASE_URL=${{Postgres.DATABASE_URL}}

5. Keep the existing ANTHROPIC/OPENAI/admin variables.
6. `TRIP_DB_PATH` is no longer needed in production; remove it if you previously created it for v3.4.
7. Save/apply the changes.

Railway will redeploy the Arrow service after variables/code change.

## Phase D — push the tested code

After local tests are clean:

    git add .
    git commit -m "Use Railway PostgreSQL for CHI trip administration"
    git push -u origin arrow-v3.5-postgres

Then merge to main only after review:

    git switch main
    git pull --ff-only origin main
    git merge --ff-only arrow-v3.5-postgres
    pytest -q
    git push origin main

## Phase E — first production test

1. Wait for the Arrow Railway deployment to show `Success`.
2. Open `/chi-admin.html` and enter the CHI admin key.
3. The trip storage status should say:

       Railway PostgreSQL connected — trip changes are persistent.

4. Confirm the tracker starts at:

       0 days reserved/used
       250 days remaining
       0 current trips
       0 travelling employees

5. Add one temporary test trip, e.g. a one-day ATH-GVA-ATH trip.
6. Confirm the dashboard becomes 1 / 1 / 249 as appropriate.
7. Delete the temporary trip and confirm it returns to 0 / 0 / 250.

The database schema is created automatically on first use. No SQL console work is required.
