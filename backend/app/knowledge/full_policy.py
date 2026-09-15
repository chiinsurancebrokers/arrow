"""Verified full-policy retrieval from the attached 39-page certificate.

The page-marked text export lives at data/policy/arrow_2026_full.txt. The structured
arrow_2026.json remains authoritative for the headline limits already verified there;
this layer adds exact definitions, conditions and less-common wording with PDF-page
provenance.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FULL_WORDING_PATH = ROOT / "data" / "policy" / "arrow_2026_full.txt"
PAGE_RE = re.compile(r"^===== POLICY PDF PAGE (\d+) =====\s*$", re.MULTILINE)
STOP = {
    "what", "when", "where", "which", "does", "have", "with", "from", "this", "that",
    "there", "would", "could", "should", "about", "against", "covered", "cover", "policy",
    "insurance", "arrow", "please", "tell", "show", "claim",
}


@lru_cache(maxsize=1)
def _pages() -> list[tuple[int, str]]:
    if not FULL_WORDING_PATH.exists():
        return []
    text = FULL_WORDING_PATH.read_text(encoding="utf-8", errors="replace")
    matches = list(PAGE_RE.finditer(text))
    pages: list[tuple[int, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            pages.append((int(match.group(1)), body))
    return pages


def full_wording_available() -> bool:
    return bool(_pages())


def _query_terms(query: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-zA-Z]{4,}", query.lower())
        if w not in STOP
    }


def relevant_full_wording(query: str, limit: int | None = None) -> str | None:
    pages = _pages()
    if not pages:
        return None
    limit = limit or max(1, min(6, int(os.getenv("HAL_FULL_POLICY_EXCERPTS", "4"))))
    max_chars = max(1500, min(12000, int(os.getenv("HAL_FULL_POLICY_MAX_CHARS", "7000"))))
    terms = _query_terms(query)
    q = query.lower().strip()

    scored: list[tuple[float, int, str]] = []
    for page_no, body in pages:
        low = body.lower()
        score = float(sum(low.count(term) for term in terms))
        # Reward exact multi-word phrases and high-value policy vocabulary.
        for phrase in ("delayed baggage", "insured journey", "external journey", "internal journey",
                       "medical expenses", "rental vehicle", "how to make a claim", "pre-existing",
                       "personal liability", "travel delay", "kidnap", "evacuation"):
            if phrase in q and phrase in low:
                score += 20.0
                # Definition/section headings are much stronger evidence than repeated mentions.
                if re.search(rf"(?im)^\s*{re.escape(phrase)}\s*$", body):
                    score += 60.0
        if score > 0:
            scored.append((score, page_no, body))

    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        return None

    chunks: list[str] = []
    used = 0
    for _, page_no, body in scored[:limit]:
        remaining = max_chars - used
        if remaining <= 300:
            break
        excerpt = body[:remaining]
        chunk = f"[Policy PDF page {page_no}]\n{excerpt}"
        chunks.append(chunk)
        used += len(chunk)
    return "\n\n---\n\n".join(chunks) if chunks else None
