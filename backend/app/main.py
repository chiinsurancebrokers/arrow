from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.chat import router as chat_router
from backend.app.knowledge.policy_facts import certificate_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"

app = FastAPI(title="Arrow Travel Portal API", version="1.0.0")

# Same-origin by default (frontend is served from this app). Loosen only if
# you split frontend/backend across two Railway services.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "certificate": certificate_summary()["certificate_no"]}


# data/policy/*.json (HAL's facts) and data/trips/*.json (season archive +
# current-year trip data) are readable at /data/... -- useful for the
# archive-card link in the frontend, or for a future admin tool.
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Serve the portal itself last, so /api/*, /health and /data/* are matched first.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
