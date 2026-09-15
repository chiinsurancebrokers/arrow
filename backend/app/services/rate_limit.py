"""Lightweight server-side usage guard for public employee HAL.

The guard deliberately applies only to AI-backed employee questions. Deterministic
claim instructions, emergency contacts and simple policy facts stay available even
when the AI allowance is exhausted.

This is process-local by design: it works immediately on a single Railway instance.
For multi-instance deployments, replace the counters with Redis/Upstash while
keeping the same public functions.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


SESSION_10MIN = _env_int("HAL_EMPLOYEE_SESSION_10MIN", 6)
SESSION_DAILY = _env_int("HAL_EMPLOYEE_SESSION_DAILY", 20)
IP_HOURLY = _env_int("HAL_EMPLOYEE_IP_HOURLY", 50)
IP_DAILY = _env_int("HAL_EMPLOYEE_IP_DAILY", 150)
GLOBAL_DAILY = _env_int("HAL_GLOBAL_AI_DAILY", 200)
COOLDOWN_SECONDS = _env_float("HAL_EMPLOYEE_COOLDOWN_SECONDS", 3.0)


@dataclass
class LimitDecision:
    allowed: bool
    retry_after: int = 0
    reason: str = ""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:24]


def _day_key(now: float) -> str:
    return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")


def _seconds_until_next_utc_day(now: float) -> int:
    dt = datetime.fromtimestamp(now, tz=timezone.utc)
    next_day = dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400
    return max(1, int(next_day - now) + 1)


class _UsageGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session_10min: dict[str, deque[float]] = defaultdict(deque)
        self._ip_hour: dict[str, deque[float]] = defaultdict(deque)
        self._session_daily: dict[tuple[str, str], int] = defaultdict(int)
        self._ip_daily: dict[tuple[str, str], int] = defaultdict(int)
        self._global_daily: dict[str, int] = defaultdict(int)
        self._last_session_call: dict[str, float] = {}

    @staticmethod
    def _trim(q: deque[float], now: float, window: float) -> None:
        cutoff = now - window
        while q and q[0] <= cutoff:
            q.popleft()

    def check_and_consume(self, session_id: str | None, ip: str | None) -> LimitDecision:
        now = time.time()
        day = _day_key(now)
        clean_session = (session_id or "").strip()[:160]
        session_key = _hash(clean_session) if clean_session else None
        ip_key = _hash((ip or "unknown-ip").strip()[:160])

        with self._lock:
            iq = self._ip_hour[ip_key]
            self._trim(iq, now, 3600)

            if session_key:
                sq = self._session_10min[session_key]
                self._trim(sq, now, 600)
                last = self._last_session_call.get(session_key)
                if last is not None and now - last < COOLDOWN_SECONDS:
                    return LimitDecision(False, max(1, int(COOLDOWN_SECONDS - (now - last)) + 1), "cooldown")
                if len(sq) >= SESSION_10MIN:
                    retry = max(1, int(600 - (now - sq[0])) + 1)
                    return LimitDecision(False, retry, "browser_10min")
                if self._session_daily[(day, session_key)] >= SESSION_DAILY:
                    return LimitDecision(False, _seconds_until_next_utc_day(now), "browser_daily")

            if len(iq) >= IP_HOURLY:
                retry = max(1, int(3600 - (now - iq[0])) + 1)
                return LimitDecision(False, retry, "ip_hourly")
            if self._ip_daily[(day, ip_key)] >= IP_DAILY:
                return LimitDecision(False, _seconds_until_next_utc_day(now), "ip_daily")
            if self._global_daily[day] >= GLOBAL_DAILY:
                return LimitDecision(False, _seconds_until_next_utc_day(now), "global_daily")

            if session_key:
                self._session_10min[session_key].append(now)
                self._session_daily[(day, session_key)] += 1
                self._last_session_call[session_key] = now
            iq.append(now)
            self._ip_daily[(day, ip_key)] += 1
            self._global_daily[day] += 1
            return LimitDecision(True)

    def snapshot(self) -> dict:
        now = time.time()
        day = _day_key(now)
        with self._lock:
            # Keep only a small operational summary; never expose raw IP/session IDs.
            return {
                "ai_requests_today_this_instance": self._global_daily[day],
                "global_daily_limit": GLOBAL_DAILY,
                "employee_browser_10min_limit": SESSION_10MIN,
                "employee_browser_daily_limit": SESSION_DAILY,
                "employee_ip_hourly_limit": IP_HOURLY,
                "employee_ip_daily_limit": IP_DAILY,
                "cooldown_seconds": COOLDOWN_SECONDS,
                "scope": "process-local; use Redis/Upstash if Railway is scaled to multiple instances",
            }


_guard = _UsageGuard()


def check_employee_ai_limit(session_id: str | None, ip: str | None) -> LimitDecision:
    return _guard.check_and_consume(session_id, ip)


def usage_snapshot() -> dict:
    return _guard.snapshot()
