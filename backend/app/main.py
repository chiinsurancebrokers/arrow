from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.chat import router as chat_router
from backend.app.knowledge.policy_facts import certificate_summary

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

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


# Serve the portal itself last, so /api/* and /health are matched first.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
