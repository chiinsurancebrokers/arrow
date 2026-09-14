# Arrow Travel Portal

Arrow Shipping Hellas's travel-insurance portal: the trip tracker, bilingual
benefits guide, and emergency contacts, now serving Certificate
**CGT P804302600** (renewal, 1 Sept 2026 – 31 Aug 2027) — plus **HAL**, a
chat assistant that explains the certificate wording.

## HAL's design principle

HAL never invents a benefit, limit, or exclusion. `data/policy/arrow_2026.json`
is the single source of truth, extracted from the certificate; Claude's
system prompt (`backend/app/services/adviser.py`) is only allowed to explain
what's in that file, and is instructed to say plainly when a question falls
outside it. `tests/test_policy_facts.py` pins the renewal figures down as
regression tests so a future edit can't silently drift from the certificate.

This is the same "deterministic facts, Claude explains" split used in
`ashlar-hal-3`, scoped down to one static verified document instead of a
live quote engine.

## Project layout

```
frontend/index.html      the portal itself (single file, no build step)
backend/app/main.py       FastAPI: serves frontend/, /health, /api/chat
backend/app/knowledge/    loads data/policy/arrow_2026.json
backend/app/services/     the Claude call + evidence-gated system prompt
backend/app/api/          /api/chat router
data/policy/arrow_2026.json   structured, verified facts from the certificate
tests/                    regression tests for both the facts and the prompt
```

## Running locally

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY
python -m pytest tests/ -v
uvicorn backend.app.main:app --reload
```

Then open http://127.0.0.1:8000/.

## Deploying (Railway)

`railway.json` is already set up: Nixpacks build, root directory `/`,
health check `/health`. Add `ANTHROPIC_API_KEY` as a Railway environment
variable, then deploy.

## What changed in this renewal (2025/26 → 2026/27)

| Item | Old | New |
|---|---|---|
| Certificate No. | CGT P804302500 CN | **CGT P804302600** |
| Period | 25/09/2025–24/09/2026 | **01/09/2026–31/08/2027** |
| Section 2 Cancellation | €7,500/person | **€15,000**/person |
| Section 3 Baggage | €5,000 | **€15,000** |
| Section 3 Business Equipment | €2,000 | **€3,000** |
| Section 4 Money | €3,000 (cash €1,500) | **€10,000** (cash **€3,000**) |
| Section 4 Rental Vehicle Excess | not tracked | **new**: €1,000/event, €25,000 aggregate |
| Any One Accident aggregate cap | not tracked | **new**: €10,000,000 |
| Kidnap-excluded countries (in-app flag list) | 10 countries | **16 countries** (added Belarus, Gaza, Israel, Lebanon, Russia, Ukraine) |
| Claims phone (Crawford TPA) | 01908 735318 (stale) | **+32 2 714 03 60** |
| War/unrest notice | time-bound March 2026 notice | evergreen Endorsements clause |

The **"250 shared days"** annual pool shown in the tracker is an Arrow/CHI
internal tracking convention, not a figure stated in the certificate itself
— it's carried forward unchanged pending confirmation from Arrow/CHI, and
is flagged as such in both the UI copy and HAL's knowledge file so it's
never presented as policy fact.

Sections 1, 5, 6, 7, 8, 9, 10 are unchanged in value from the prior policy.
