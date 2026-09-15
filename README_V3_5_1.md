# Arrow v3.5.1 — HAL history 422 hotfix

Fixes two console/browser issues:

1. A long HAL response in conversation history could make the NEXT `/api/chat`
   request fail FastAPI validation with HTTP 422.
2. The obsolete Cloudflare `email-decode.min.js` script produced a harmless 404.

## Root cause

`ChatTurn.content` accepted max 1,500 chars at request validation time, while the
browser stored the full HAL answer. `adviser._normalise_history()` already
truncated history to 1,500 chars, but validation happened before that function
could run.

## Fix

- Browser trims outgoing HAL history to 1,500 chars/item, last 10 turns.
- API accepts history items up to 6,000 chars for resilience.
- Adviser remains the authoritative token guard: 1,500 chars/item and 6,000
  chars total before calling Claude/OpenAI.
- Adds regression test with a 3,000-character previous answer.
- Formats FastAPI validation details as readable text instead of `[object Object]`.
- Removes unused `/cdn-cgi/.../email-decode.min.js`.

## Apply on top of v3.5

    unzip -o ../arrow-v3.5.1-hal-history-hotfix.zip
    python tools/apply_v351.py
    pytest -q
    git diff --check

Expected: existing suite plus 2 regression tests.
