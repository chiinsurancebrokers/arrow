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
from backend.app.api.tracker import router as tracker_router
from backend.app.knowledge.policy_facts import certificate_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"

app = FastAPI(title="Arrow Travel Portal API", version="3.5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET", "PUT", "DELETE"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(tracker_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "certificate": certificate_summary()["certificate_no"], "hal_version": "3.5"}


@app.get("/", response_class=HTMLResponse)
def employee_portal() -> HTMLResponse:
    """Serve the employee portal with HAL and live current-year tracker assets."""
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    css_assets = ["/hal-v2.css", "/tracker-v3.4.css"]
    js_assets = ["/hal-v2.js", "/tracker-v3.4.js"]

    for asset in css_assets:
        if asset not in html:
            html = html.replace("</head>", f'<link rel="stylesheet" href="{asset}">\n</head>')

    for asset in js_assets:
        if asset not in html:
            html = html.replace("</body>", f'<script src="{asset}"></script>\n</body>')

    return HTMLResponse(html)


# Historical/current source data are NOT mounted as public static files.
# The employee portal gets only the current policy year via /api/tracker/current.
# Archive/history is available through authenticated Arrow-admin endpoints.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
