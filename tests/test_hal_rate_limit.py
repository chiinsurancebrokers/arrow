from backend.app.services import rate_limit as rl


def test_browser_window_blocks_third_call(monkeypatch):
    monkeypatch.setattr(rl, "SESSION_10MIN", 2)
    monkeypatch.setattr(rl, "SESSION_DAILY", 50)
    monkeypatch.setattr(rl, "IP_HOURLY", 50)
    monkeypatch.setattr(rl, "IP_DAILY", 100)
    monkeypatch.setattr(rl, "GLOBAL_DAILY", 100)
    monkeypatch.setattr(rl, "COOLDOWN_SECONDS", 0.0)
    guard = rl._UsageGuard()
    assert guard.check_and_consume("browser-a", "1.2.3.4").allowed
    assert guard.check_and_consume("browser-a", "1.2.3.4").allowed
    third = guard.check_and_consume("browser-a", "1.2.3.4")
    assert not third.allowed
    assert third.reason == "browser_10min"


def test_different_browser_still_hits_shared_ip_guard(monkeypatch):
    monkeypatch.setattr(rl, "SESSION_10MIN", 50)
    monkeypatch.setattr(rl, "SESSION_DAILY", 50)
    monkeypatch.setattr(rl, "IP_HOURLY", 2)
    monkeypatch.setattr(rl, "IP_DAILY", 100)
    monkeypatch.setattr(rl, "GLOBAL_DAILY", 100)
    monkeypatch.setattr(rl, "COOLDOWN_SECONDS", 0.0)
    guard = rl._UsageGuard()
    assert guard.check_and_consume("browser-a", "1.2.3.4").allowed
    assert guard.check_and_consume("browser-b", "1.2.3.4").allowed
    third = guard.check_and_consume("browser-c", "1.2.3.4")
    assert not third.allowed
    assert third.reason == "ip_hourly"
