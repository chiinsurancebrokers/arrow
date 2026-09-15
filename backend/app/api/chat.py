from __future__ import annotations

import logging
import os
import re

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.knowledge.policy_facts import load_policy_facts
from backend.app.services.adviser import HalReply, ask_hal
from backend.app.services.rate_limit import check_employee_ai_limit

router = APIRouter()
logger = logging.getLogger("hal.chat")


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=1500)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1200)
    history: list[ChatTurn] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    provider: str = "deterministic"
    mode: str = "policy_guidance"
    quick_actions: list[str] = Field(default_factory=list)


def _claim_steps() -> HalReply:
    c = load_policy_facts()["claims_process"]
    answer = (
        "**How to claim**\n\n"
        "1. Notify Crawford TPA as soon as practicable and no later than the policy's maximum notification period of 6 months.\n"
        "2. If an accident or illness abroad may lead to hospital treatment or curtailment, contact Healix International's 24-hour medical emergency helpline.\n"
        f"3. Online claim form: {c['online_form']}\n"
        f"4. Crawford: {c['crawford_phone']} | {c['crawford_email']}\n"
        "5. Provide the requested supporting documents and a completed claim form. For a death claim, notify your broker as soon as practicable.\n\n"
        "CHI Insurance Brokers can help you understand the procedure, but final assessment is made by the insurer/claims handler.\n\n"
        "Source: How to Make a Claim, policy PDF page 15."
    )
    return HalReply(answer=answer, citations=["Policy PDF page 15"], provider="deterministic", mode="claim_procedure")


def _who_to_call(message: str) -> HalReply:
    facts = load_policy_facts()["claims_process"]
    m = message.lower()
    if re.search(r"kidnap|abduct|security|hostage|detention", m):
        answer = f"For a kidnap/security incident, contact **Constellis immediately**. {facts['kidnap_response']}\n\nSource: Policy PDF page 17 / Section 7."
        cites = ["Policy PDF page 17", "Section 7"]
    elif re.search(r"medical|hospital|doctor|ill|injur|repatri|ambulance|emergency", m):
        answer = f"For a medical emergency or medical assistance, contact **Healix International 24/7**: {facts['medical_emergency_helpline']}\n\nSource: Policy PDF page 17."
        cites = ["Policy PDF page 17"]
    else:
        answer = f"For a standard insurance claim, contact **Crawford TPA**: {facts['crawford_phone']} | {facts['crawford_email']}. You can also ask CHI Insurance Brokers to assist with the procedure.\n\nSource: Policy PDF page 15."
        cites = ["Policy PDF page 15"]
    return HalReply(answer=answer, citations=cites, provider="deterministic", mode="contact_guidance")


def _intent(message: str) -> str:
    m = message.lower().strip()
    if re.search(r"how (do|can|should) i claim|how to claim|claim procedure|submit.*claim|make.*claim", m):
        return "claim_procedure"
    if re.search(r"who.*call|who.*contact|phone number|contact number|emergency number", m):
        return "contact_guidance"
    if re.search(r"am i covered|is .* covered|does .* cover|covered against|covered if|covered for", m):
        return "coverage_question"
    return "policy_guidance"


def _simple_policy_fact(message: str) -> HalReply | None:
    facts = load_policy_facts()
    sec = facts["sections"]
    cert = facts["certificate"]
    m = message.lower()
    if re.search(r"policy number|certificate number|certificate no", m):
        return HalReply(answer=f"The active Arrow certificate is **{cert['certificate_no']}**.\n\nSource: Policy PDF page 3.", citations=["Policy PDF page 3"], provider="deterministic", mode="policy_fact")
    if re.search(r"when.*(expire|end)|expiry|period of insurance|valid until", m):
        return HalReply(answer=f"The current period of insurance is **{cert['period_of_insurance']}**.\n\nSource: Policy PDF page 3.", citations=["Policy PDF page 3"], provider="deterministic", mode="policy_fact")
    if re.search(r"medical.*(limit|cover|amount)|how much.*medical", m):
        return HalReply(answer=f"Medical Expenses, Repatriation and Emergency Travel Expenses have a stated sum insured of **€{sec['1']['sum_insured_eur']:,}**, subject to the section terms and exclusions.\n\nSource: Schedule page 4; Section 1 pages 20–22.", citations=["Policy PDF page 4", "Section 1, pages 20–22"], provider="deterministic", mode="policy_fact")
    if re.search(r"baggage.*(limit|cover|amount)|how much.*baggage", m):
        return HalReply(answer=f"Baggage has a stated sum insured of **€{sec['3']['sum_insured_eur']:,}**, with a **€{sec['3']['single_item_limit_eur']:,}** single-item limit. The Section 3 delayed-baggage benefit is up to **€{sec['3']['delayed_baggage_reimbursement_eur']:,}** when baggage is lost for more than **{sec['3']['delayed_baggage_threshold_hours']} hours** during outward/onward journeys.\n\nSource: Policy PDF pages 4 and 24.", citations=["Policy PDF page 4", "Policy PDF page 24"], provider="deterministic", mode="policy_fact")
    if re.search(r"cancellation.*(limit|cover|amount)|how much.*cancellation", m):
        return HalReply(answer=f"Cancellation/Curtailment/Replacement/Change of Itinerary has a stated limit of **€{sec['2']['sum_insured_eur_per_person']:,} per person**, with a **€{sec['2']['incident_limit_eur']:,}** incident limit, subject to the wording.\n\nSource: Policy PDF pages 4 and 23.", citations=["Policy PDF page 4", "Policy PDF page 23"], provider="deterministic", mode="policy_fact")
    if re.search(r"cash.*(limit|cover)|money.*(limit|cover)", m):
        return HalReply(answer=f"Section 4 has a stated sum insured of **€{sec['4']['sum_insured_eur']:,}**, including a cash limit of **€{sec['4']['cash_limit_eur']:,}**.\n\nSource: Policy PDF pages 4 and 25.", citations=["Policy PDF page 4", "Policy PDF page 25"], provider="deterministic", mode="policy_fact")
    if re.search(r"personal liability.*(limit|cover)|liability.*how much", m):
        return HalReply(answer=f"The Personal Liability limit is **€{sec['6']['personal_liability_eur']:,}**, subject to Section 6 terms and exclusions.\n\nSource: Schedule page 4; Section 6 pages 30–31.", citations=["Policy PDF page 4", "Section 6, pages 30–31"], provider="deterministic", mode="policy_fact")
    if re.search(r"age limit|maximum age|too old", m):
        return HalReply(answer=f"{facts['age_limit']}\n\nSource: Policy conditions / age limit.", citations=["Policy conditions / age limit"], provider="deterministic", mode="policy_fact")
    return None


def _looks_policy_related(message: str, history: list[ChatTurn]) -> bool:
    text = " ".join([message] + [t.content for t in history[-2:]]).lower()
    terms = (
        "cover", "claim", "policy", "insurance", "travel", "trip", "journey", "flight", "delay", "cancel",
        "baggage", "bag", "luggage", "lost", "stolen", "theft", "rob", "phone", "laptop", "passport", "money",
        "cash", "medical", "doctor", "hospital", "ill", "sick", "injur", "accident", "dental", "repatri", "evacuat",
        "kidnap", "security", "liability", "rental", "car", "vehicle", "war", "unrest", "sport", "ski", "scuba",
        "employee", "spouse", "child", "country", "destination", "healix", "crawford", "constellis", "benefit",
    )
    return any(term in text for term in terms)


def _client_ip(request: Request) -> str:
    # Railway/proxy usually provides X-Forwarded-For. Only the first hop is used,
    # and it is a secondary abuse guard; browser-session limits remain primary.
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:100]
    return request.client.host[:100] if request.client else "unknown"


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    x_hal_session: str | None = Header(default=None),
) -> ChatResponse:
    intent = _intent(payload.message)
    simple = _simple_policy_fact(payload.message)
    if simple is not None:
        reply = simple
    elif intent == "claim_procedure":
        reply = _claim_steps()
    elif intent == "contact_guidance":
        reply = _who_to_call(payload.message)
    elif not _looks_policy_related(payload.message, payload.history):
        reply = HalReply(
            answer=(
                "HAL is limited to Arrow's travel-insurance cover, claims procedures and emergency contacts. "
                "Please ask a question about your trip, cover, baggage, medical assistance, cancellation, security or a claim."
            ),
            provider="guard",
            mode="scope_guard",
        )
    else:
        decision = check_employee_ai_limit(x_hal_session, _client_ip(request))
        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    "HAL's AI question allowance has been reached for now to protect the service from overuse. "
                    "Emergency contacts, 'Show me how to claim', and simple policy-limit questions remain available. "
                    "Please try an AI question again later."
                ),
                headers={"Retry-After": str(decision.retry_after)},
            )
        try:
            reply = await ask_hal(payload.message, history=[turn.model_dump() for turn in payload.history])
            reply.mode = "coverage_guidance" if intent == "coverage_question" else "policy_guidance"
        except Exception as exc:  # noqa: BLE001
            logger.exception("HAL /api/chat failed for message: %r", payload.message)
            detail = "HAL is temporarily unavailable. Claims contacts and emergency guidance remain available from the portal."
            if os.getenv("HAL_DEBUG") == "1":
                detail += f" Debug: {type(exc).__name__}: {exc}"
            raise HTTPException(status_code=502, detail=detail) from exc

    return ChatResponse(**reply.__dict__)
