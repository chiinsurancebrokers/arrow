from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.admin import router as admin_router
from backend.app.api.chat import router as chat_router
from backend.app.knowledge.policy_facts import certificate_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"

app = FastAPI(title="Arrow Travel Portal API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "certificate": certificate_summary()["certificate_no"], "hal_version": "2"}


@app.get("/", response_class=HTMLResponse)
def employee_portal() -> HTMLResponse:
    """Serve the existing portal untouched, injecting the HAL v2 enhancement assets."""
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    if "/hal-v2.css" not in html:
        html = html.replace("</head>", '<link rel="stylesheet" href="/hal-v2.css">\n</head>')
    if "/hal-v2.js" not in html:
        html = html.replace("</body>", '<script src="/hal-v2.js"></script>\n</body>')
    return HTMLResponse(html)


app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
# Existing frontend remains available, including arrow-admin.html and chi-admin.html.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
