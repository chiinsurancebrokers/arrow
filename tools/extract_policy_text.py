"""Renewal helper: create HAL's page-marked full-policy text from a PDF.
Usage: python tools/extract_policy_text.py path/to/policy.pdf data/policy/arrow_2026_full.txt
"""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
import fitz

if len(sys.argv) != 3:
    raise SystemExit("Usage: python tools/extract_policy_text.py INPUT.pdf OUTPUT.txt")
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
doc = fitz.open(src)
parts = []
for page_no, page in enumerate(doc, 1):
    parts.append(f"===== POLICY PDF PAGE {page_no} =====\n{page.get_text('text').strip()}\n")
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {len(doc)} pages to {dst}")
print("SHA256:", hashlib.sha256(src.read_bytes()).hexdigest())
