"""
Loads the single source of truth for HAL: the structured, verified facts
extracted from Certificate CGT P804302600 (data/policy/arrow_2026.json).

This module is the "deterministic layer" in the HAL pattern. Nothing in
backend/app/services/adviser.py is allowed to state a figure or exclusion
that isn't present here -- the whole JSON is handed to Claude as its only
grounding, and the system prompt in adviser.py instructs it to say so
explicitly when something isn't covered by this document.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "policy" / "arrow_2026.json"


@lru_cache(maxsize=1)
def load_policy_facts() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def policy_facts_as_json_str() -> str:
    """Compact-ish JSON string for embedding directly in the system prompt."""
    return json.dumps(load_policy_facts(), ensure_ascii=False, indent=2)


def certificate_summary() -> dict:
    """Small, cheap-to-render subset for a /api/policy-summary endpoint if wanted."""
    facts = load_policy_facts()
    cert = facts["certificate"]
    return {
        "certificate_no": cert["certificate_no"],
        "period_of_insurance": cert["period_of_insurance"],
        "assured": cert["assured"],
        "underwriter": cert["underwriter"],
    }
