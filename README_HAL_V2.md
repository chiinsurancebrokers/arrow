# HAL v3 overlay - Arrow / CHI

This ZIP is an **overlay** for `chiinsurancebrokers/arrow`. Extract it at the repository root. It replaces/adds only the listed paths and does not overwrite the large existing `frontend/index.html`, the current trip JSON, or the structured `data/policy/arrow_2026.json`.

## What HAL v3 adds

- Claude remains the primary AI provider; OpenAI is the automatic fallback.
- The duplicate-current-question bug is removed server-side.
- Employee HAL separates **policy cover guidance** from an individual **claim decision**.
- Employee quick actions: **Am I covered if... / Show me how to claim / Who should I call?**
- Claim instructions and emergency/contact routing are deterministic, so they still work if both AI providers are down or an employee reaches the AI allowance.
- Arrow tracker/day-pool intelligence is available only to authenticated **Arrow Administrator**.
- **CHI Insurance Administrator** receives policy/claims administration, provider health and employee-usage-guard status, but no Arrow tracker/day-pool data.
- The attached original 39-page policy has been converted to `data/policy/arrow_2026_full.txt`, with `===== POLICY PDF PAGE N =====` markers. Complex questions can now retrieve the full wording and cite the original PDF page.
- Employee anti-overuse controls limit AI-backed questions by browser session, IP and total daily requests. Simple limits, claim instructions and emergency contacts do not spend the AI allowance.
- AI responses are capped by `HAL_MAX_OUTPUT_TOKENS`; chat history and retrieved full-policy excerpts are also capped to reduce repeated input-token cost.
- Unrelated prompts (coding, essays, general knowledge, etc.) are rejected without calling Claude/OpenAI.

## Default employee safeguards

Defaults are deliberately conservative and are configurable in Railway:

```text
HAL_EMPLOYEE_COOLDOWN_SECONDS=3
HAL_EMPLOYEE_SESSION_10MIN=6
HAL_EMPLOYEE_SESSION_DAILY=20
HAL_EMPLOYEE_IP_HOURLY=50
HAL_EMPLOYEE_IP_DAILY=150
HAL_GLOBAL_AI_DAILY=200
HAL_MAX_OUTPUT_TOKENS=550
```

The browser creates a random local HAL session id. The backend combines session, IP and a global process-level ceiling. Raw IP/session values are not exposed in the CHI dashboard.

The built-in limiter is process-local and is appropriate for one Railway instance. If the service is later scaled horizontally to multiple instances, move the counters to Redis/Upstash for a shared global quota.

## Full-policy source

The supplied PDF is 39 pages. `data/policy/arrow_2026_source.json` records its SHA-256 and the extracted text source.

Because the GitHub repository is public, this package **does not commit the original binary PDF**. The page-marked text is sufficient for HAL retrieval. If you later make the repository private and want the original PDF stored there too, add it deliberately after reviewing access.

See `POLICY_REVIEW.md` for verified anchors and the delayed-baggage wording discrepancy that HAL must preserve.

## Railway variables

```text
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
HAL_MODEL=claude-sonnet-4-6
HAL_OPENAI_MODEL=gpt-5.6-luna
HAL_REQUEST_TIMEOUT=30
HAL_MAX_OUTPUT_TOKENS=550
HAL_FULL_POLICY_EXCERPTS=4
HAL_FULL_POLICY_MAX_CHARS=7000

HAL_EMPLOYEE_COOLDOWN_SECONDS=3
HAL_EMPLOYEE_SESSION_10MIN=6
HAL_EMPLOYEE_SESSION_DAILY=20
HAL_EMPLOYEE_IP_HOURLY=50
HAL_EMPLOYEE_IP_DAILY=150
HAL_GLOBAL_AI_DAILY=200

ARROW_ADMIN_KEY=<long-random-secret>
CHI_ADMIN_KEY=<different-long-random-secret>
HAL_DEBUG=0
```

## URLs after deployment

- Employee portal: `/`
- Arrow administrator: `/arrow-admin.html`
- CHI Insurance administrator: `/chi-admin.html`
- Health check: `/health`

## Admin-key note

The access-key pages are a pragmatic first gate. For broader production use, replace them with user accounts/SSO and server-side sessions. Never share the CHI key with Arrow users.

### v3.1 test-compatibility note
This bundle also replaces the two original HAL regression tests so they exercise
AI-backed policy questions rather than deterministic/guard responses, and target
the v3 grounding API (`build_system_prompt`).
