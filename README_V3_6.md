# Arrow v3.6 — policy allocation + corrected renewal accounting

Apply on top of v3.5 / v3.5.1.

## Correct prior-period accounting

The 2025/26 administrative pool is corrected from 247 to **250 / 250**:

- Myrsini Andreou, 16–18 Sep 2026, ATH-GVA-ATH: **3 pool days**
  - allocated to the previous pool
  - final deduction that exhausted 250/250
- Pierre Loth, 1–4 Sep 2026, ATH-GVA-ATH: **4 travel days / 0 pool days**
  - retained in the historical record
  - marked Pulse goodwill approval / exception

Archive summary becomes:

- 250 pool days used
- 57 pool-counted trips
- 1 goodwill exception
- 6 cancelled trips
- 30 employees

## Confirmed 2026/27 preloaded trips

- KOSTOPOULOS KONSTANTINOS — 02–04 Sep — ATH-GVA-ATH — 3
- MAXIMILLIAN KATSAROS — 15–18 Sep — ATH-GVA-ATH — 4
- ODYSSEAS RENIERIS — 24–30 Oct — ATH-SIN-ATH — 7
- CONSTANTINE MARK HADJIPATERAS — 07–15 Nov — ATH-DXB-ATH — 9

Initial current-pool live total after seed: **23 used/reserved / 227 remaining**.

## PostgreSQL schema migration

Existing v3.5 databases are migrated automatically with:

- `policy_allocation`
- `pool_charge_days`
- `goodwill_exception`
- `approval_note`

No manual SQL is required.

A one-time seed marker prevents the four confirmed trips from being re-created if
an administrator later edits or deletes one.

## CHI Admin

Ordinary trips: leave Pool charge days blank; full duration is deducted.

Exceptional cases: CHI can explicitly set a lower/zero pool charge and mark
Goodwill / approved exception with an approval note.

## Install

    unzip -o ../arrow-v3.6-policy-allocation.zip
    python tools/apply_v36.py
    pytest -q
    git diff --check
