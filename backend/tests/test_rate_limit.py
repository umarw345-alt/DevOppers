from backend.auth_service.rate_limit import LoginRateLimiter


def test_rate_limiter_allows_only_configured_attempts():
    limiter = LoginRateLimiter(limit=2, window_seconds=300)

    assert limiter.allow("client") is True
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False


def test_rate_limiter_tracks_keys_independently():
    limiter = LoginRateLimiter(limit=1, window_seconds=300)

    assert limiter.allow("first") is True
    assert limiter.allow("second") is True
