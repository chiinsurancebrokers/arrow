"""Regression tests for HAL v3 grounding and role separation."""

from backend.app.services.adviser import build_system_prompt


def test_system_prompt_embeds_full_policy_facts():
    prompt = build_system_prompt()
    assert "CGT P804302600" in prompt
    assert '"sum_insured_eur_per_person": 15000' in prompt
    assert "not_in_this_document" in prompt


def test_system_prompt_forbids_inventing_and_claim_adjudication():
    prompt = build_system_prompt()
    assert "Never invent" in prompt
    assert "CLAIM DECISION" in prompt
    assert "may never approve, reject, guarantee or predict an individual claim" in prompt


def test_employee_prompt_labels_tracker_as_non_policy():
    prompt = build_system_prompt()
    assert "250-day shared pool" in prompt
    assert "not policy wording" in prompt


def test_admin_tracker_context_is_explicitly_labelled_administrative():
    prompt = build_system_prompt(tracker_context='{"annual_day_limit":250}')
    assert "ADMIN CONTEXT (not policy wording)" in prompt
    assert '"annual_day_limit":250' in prompt
