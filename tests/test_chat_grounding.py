"""Regression test for HAL's core promise: it must never invent a figure
that isn't in the policy-facts JSON, and it must clearly decline questions
about things the certificate doesn't cover (e.g. individual claim outcomes,
or Arrow's internal 250-day tracking convention).

This test mocks the Anthropic client so it runs without a live API key --
it checks the *prompt construction*, not model output quality. A slower,
real-API smoke test can be added separately once ANTHROPIC_API_KEY is
available in CI.
"""

from backend.app.services.adviser import _build_system_prompt


def test_system_prompt_embeds_full_policy_facts():
    prompt = _build_system_prompt()
    assert "CGT P804302600" in prompt
    assert '"sum_insured_eur_per_person": 15000' in prompt  # Section 2 renewal figure
    assert "not_in_this_document" in prompt


def test_system_prompt_forbids_inventing_facts():
    prompt = _build_system_prompt()
    assert "may only state facts" in prompt
    assert "I can't confirm that from the certificate wording" in prompt


def test_system_prompt_refuses_claim_adjudication():
    prompt = _build_system_prompt()
    assert "not a claims handler" in prompt
