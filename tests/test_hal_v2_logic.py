import asyncio
from unittest.mock import AsyncMock, patch

from backend.app.api.chat import _intent, _looks_policy_related
from backend.app.knowledge.full_policy import full_wording_available, relevant_full_wording
from backend.app.services.adviser import _normalise_history, ask_hal


def test_duplicate_current_user_message_is_removed():
    h = [{"role": "user", "content": "Is baggage covered?"}]
    result = _normalise_history(h, "Is baggage covered?")
    assert result == [{"role": "user", "content": "Is baggage covered?"}]


def test_claim_intents():
    assert _intent("show me how to claim") == "claim_procedure"
    assert _intent("who should I call for a medical emergency?") == "contact_guidance"
    assert _intent("am I covered if my bag is stolen?") == "coverage_question"


def test_scope_guard_recognises_normal_employee_scenarios():
    assert _looks_policy_related("My phone was stolen on the trip", [])
    assert _looks_policy_related("The airline lost my baggage", [])
    assert not _looks_policy_related("Write me Python code for a game", [])


def test_full_policy_is_loaded_and_definition_page_is_retrieved():
    assert full_wording_available()
    text = relevant_full_wording("What is an Insured Journey?") or ""
    assert "Policy PDF page 11" in text
    assert "Insured Journey" in text


def test_delayed_baggage_specific_section_is_retrieved():
    text = relevant_full_wording("When is delayed baggage covered?") or ""
    assert "Policy PDF page 24" in text
    assert "more than 12 hours" in text


def test_openai_is_used_when_claude_fails():
    async def run():
        with patch("backend.app.services.adviser._ask_claude", new=AsyncMock(side_effect=RuntimeError("claude down"))), patch(
            "backend.app.services.adviser._ask_openai", new=AsyncMock(return_value="Grounded fallback answer")
        ):
            reply = await ask_hal("What is covered?")
            assert reply.provider == "openai"
            assert reply.answer == "Grounded fallback answer"
    asyncio.run(run())
