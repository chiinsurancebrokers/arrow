"""HAL v2: grounded policy explainer with Claude -> OpenAI fallback.

Public employee HAL receives policy facts only. Admin HAL may additionally receive
Arrow's internal trip-tracker context, but that context is labelled administrative
and must never be represented as policy wording.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from backend.app.knowledge.policy_facts import policy_facts_as_json_str
from backend.app.knowledge.full_policy import relevant_full_wording

logger = logging.getLogger("hal.adviser")
CLAUDE_MODEL = os.getenv("HAL_MODEL", "claude-sonnet-4-6")
OPENAI_MODEL = os.getenv("HAL_OPENAI_MODEL", "gpt-5.6-luna")
TIMEOUT = float(os.getenv("HAL_REQUEST_TIMEOUT", "30"))
MAX_OUTPUT_TOKENS = max(200, min(900, int(os.getenv("HAL_MAX_OUTPUT_TOKENS", "550"))))

SYSTEM_PROMPT = """You are HAL, the policy assistant in Arrow Shipping Hellas's travel insurance portal.
You explain Group Travel Insurance Certificate CGT P804302600 (Pulse Europe / Lloyd's Insurance Company S.A.).

NON-NEGOTIABLE RULES:
1. POLICY FACTS JSON below is your authoritative source for benefits, limits, exclusions, contacts and procedures.
2. Never invent, estimate, round, infer or import a policy fact from general insurance knowledge.
3. If the answer is not supported by the supplied evidence, say that you cannot confirm it from the available policy wording and direct the employee to CHI Insurance Brokers / the relevant assistance provider.
4. Distinguish POLICY COVER GUIDANCE from a CLAIM DECISION. You may explain whether wording appears relevant to a scenario, but you may never approve, reject, guarantee or predict an individual claim.
5. When asked 'am I covered against/if/for ...', explain the relevant cover, conditions and exclusions and explicitly state that final claim acceptance depends on the actual circumstances and insurer/claims handler assessment.
6. When asked how to claim, give practical steps using only the claims/contact facts supplied.
7. When asked who to call, prioritise the correct provider: Healix for medical emergency/assistance, Constellis for kidnap/security, Crawford TPA for ordinary claims, CHI Insurance Brokers when broker help/clarification is needed.
8. The 250-day shared pool and tracker warning thresholds are internal Arrow/CHI administration, not policy wording. Public employee HAL must not claim they are insurance benefits or restrictions.
9. Respond in the same language as the user.
10. Keep answers clear and useful. Start coverage-scenario answers with **Policy cover guidance — not a claim decision** and end with a short 'Source:' line naming the section/page when available.
11. The active certificate is CGT P804302600 for 1 September 2026 to 31 August 2027. Do not apply its terms to an event before 1 September 2026; state that the event belongs to an earlier policy period and must be checked against that earlier certificate.
12. If FULL POLICY EXCERPTS are supplied below, use them to clarify definitions/conditions and cite the exact PDF page shown in the excerpt. Structured POLICY FACTS remain authoritative for listed limits and values.
13. Known wording point: the General Definition on PDF page 10 describes Delayed Baggage using at least 4 hours, while the specific Section 3 benefit on PDF page 24 requires baggage to be lost for more than 12 hours before the €1,000 reimbursement applies. For benefit guidance, state the Section 3 payment trigger and disclose this wording discrepancy if relevant; do not make a legal interpretation resolving the conflict.
14. Do not perform unrelated tasks, creative writing, coding, general knowledge or other non-policy work. HAL is only for Arrow travel insurance, claims and related travel-assistance guidance.

POLICY FACTS JSON:
{policy_facts}
"""

FULL_WORDING_APPENDIX = """

FULL POLICY EXCERPTS (verified text, only when available):
{full_wording}
"""

ADMIN_APPENDIX = """

ADMIN CONTEXT (not policy wording):
The following is internal Arrow/CHI tracker information. You may use it only because this is an authenticated administrator conversation. Always label tracker/day-pool information as administrative, never as an insurance term.
{tracker_context}
"""


@dataclass
class HalReply:
    answer: str
    citations: list[str] = field(default_factory=list)
    provider: str = ""
    mode: str = "policy_guidance"
    quick_actions: list[str] = field(default_factory=lambda: [
        "Am I covered if…",
        "Show me how to claim",
        "Who should I call?",
    ])


def build_system_prompt(*, tracker_context: str | None = None, full_wording: str | None = None) -> str:
    prompt = SYSTEM_PROMPT.format(policy_facts=policy_facts_as_json_str())
    if full_wording:
        prompt += FULL_WORDING_APPENDIX.format(full_wording=full_wording)
    if tracker_context:
        prompt += ADMIN_APPENDIX.format(tracker_context=tracker_context)
    return prompt


def _extract_citations(text: str) -> list[str]:
    refs: list[str] = []
    for line in text.splitlines():
        if line.strip().lower().startswith("source:"):
            value = line.split(":", 1)[1].strip()
            if value and value not in refs:
                refs.append(value)
    return refs


def _normalise_history(history: list[dict] | None, message: str) -> list[dict]:
    messages = []
    for m in history or []:
        if m.get("role") in {"user", "assistant"} and m.get("content"):
            messages.append({"role": m["role"], "content": str(m["content"])[:1500]})
    # Older frontend versions already append the current user message before POSTing.
    # Avoid sending that same question twice.
    if messages and messages[-1].get("role") == "user" and messages[-1].get("content", "").strip() == message.strip():
        messages = messages[:-1]
    messages.append({"role": "user", "content": message})
    messages = messages[-10:]
    # Cap carried conversation text so a long chat cannot repeatedly resend a huge prompt.
    total = 0
    kept = []
    for item in reversed(messages):
        content = item["content"]
        if total + len(content) > 6000 and kept:
            break
        kept.append(item)
        total += len(content)
    return list(reversed(kept))


async def _ask_claude(system: str, messages: list[dict]) -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = await asyncio.wait_for(
        client.messages.create(model=CLAUDE_MODEL, max_tokens=MAX_OUTPUT_TOKENS, system=system, messages=messages),
        timeout=TIMEOUT,
    )
    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()


async def _ask_openai(system: str, messages: list[dict]) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured")
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await asyncio.wait_for(
        client.responses.create(
            model=OPENAI_MODEL,
            instructions=system,
            input=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
        timeout=TIMEOUT,
    )
    return (response.output_text or "").strip()


async def ask_hal(message: str, history: list[dict] | None = None, *, tracker_context: str | None = None) -> HalReply:
    messages = _normalise_history(history, message)
    system = build_system_prompt(tracker_context=tracker_context, full_wording=relevant_full_wording(message))
    errors: list[str] = []

    try:
        text = await _ask_claude(system, messages)
        if text:
            return HalReply(answer=text, citations=_extract_citations(text), provider="claude")
        raise RuntimeError("Claude returned an empty response")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Claude: {type(exc).__name__}: {exc}")
        logger.warning("Claude failed; trying OpenAI fallback: %s", errors[-1])

    try:
        text = await _ask_openai(system, messages)
        if text:
            return HalReply(answer=text, citations=_extract_citations(text), provider="openai")
        raise RuntimeError("OpenAI returned an empty response")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"OpenAI: {type(exc).__name__}: {exc}")
        logger.exception("Both HAL providers failed")

    raise RuntimeError(" | ".join(errors))
