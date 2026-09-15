"""Regression tests for HAL provider failure handling.

The prompt used here must be policy-related but not one of HAL's deterministic
quick answers, otherwise the request is intentionally answered without calling an
AI provider.
"""

import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
QUESTION = "Is my laptop covered if it is stolen from my hotel room?"


def test_chat_failure_returns_generic_message_by_default():
    os.environ.pop("HAL_DEBUG", None)
    with patch(
        "backend.app.api.chat.ask_hal",
        new=AsyncMock(side_effect=RuntimeError("boom: invalid api key")),
    ):
        res = client.post("/api/chat", json={"message": QUESTION})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert "temporarily unavailable" in detail
    assert "boom" not in detail


def test_chat_failure_echoes_real_error_when_hal_debug_enabled():
    os.environ["HAL_DEBUG"] = "1"
    try:
        with patch(
            "backend.app.api.chat.ask_hal",
            new=AsyncMock(side_effect=RuntimeError("boom: invalid api key")),
        ):
            res = client.post("/api/chat", json={"message": QUESTION})
        assert res.status_code == 502
        detail = res.json()["detail"]
        assert "RuntimeError" in detail
        assert "boom: invalid api key" in detail
    finally:
        os.environ.pop("HAL_DEBUG", None)
