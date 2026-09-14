"""Regression test for the bug this was actually built to fix: a failure in
ask_hal() must be logged (not silently swallowed) and, when HAL_DEBUG=1,
the real exception must reach the response so a deploy issue is visible
without having to dig through platform logs."""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_chat_failure_returns_generic_message_by_default():
    os.environ.pop("HAL_DEBUG", None)
    with patch(
        "backend.app.api.chat.ask_hal",
        new=AsyncMock(side_effect=RuntimeError("boom: invalid api key")),
    ):
        res = client.post("/api/chat", json={"message": "hi"})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert detail == "HAL is temporarily unavailable."
    assert "boom" not in detail


def test_chat_failure_echoes_real_error_when_hal_debug_enabled():
    os.environ["HAL_DEBUG"] = "1"
    try:
        with patch(
            "backend.app.api.chat.ask_hal",
            new=AsyncMock(side_effect=RuntimeError("boom: invalid api key")),
        ):
            res = client.post("/api/chat", json={"message": "hi"})
        assert res.status_code == 502
        detail = res.json()["detail"]
        assert "RuntimeError" in detail
        assert "boom: invalid api key" in detail
    finally:
        os.environ.pop("HAL_DEBUG", None)
