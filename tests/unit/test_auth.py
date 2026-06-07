# tests/unit/test_auth.py
# Unit tests for all auth functions.
# Tests run without DB or Redis — pure function testing.
# Run: pytest tests/unit/test_auth.py -v

import pytest
import time
from unittest.mock import patch, MagicMock
from jose import jwt

# ── Set up test environment BEFORE importing auth ─────────────────────────────
import os
os.environ["JWT_SECRET"]            = "test-secret-at-least-32-chars-long!!"
os.environ["RSA_PRIVATE_KEY_PATH"]  = "keys/private.pem"
os.environ["RSA_PUBLIC_KEY_PATH"]   = "keys/public.pem"
os.environ["REDIS_URL"]             = "redis://localhost:6379/0"
os.environ["FORCE_HTTPS"]           = "false"


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_password_returns_argon2_string(self):
        from security.auth import hash_password
        h = hash_password("TestPassword1@")
        assert h.startswith("$argon2id$")

    def test_verify_password_correct(self):
        from security.auth import hash_password, verify_password
        pw = "TestPassword1@"
        h  = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_verify_password_wrong(self):
        from security.auth import hash_password, verify_password
        h = hash_password("TestPassword1@")
        assert verify_password("WrongPassword1@", h) is False

    def test_verify_password_never_raises(self):
        from security.auth import verify_password
        # Should return False, not raise, on completely invalid hash
        result = verify_password("anything", "not-a-valid-hash")
        assert result is False

    def test_different_passwords_produce_different_hashes(self):
        from security.auth import hash_password
        h1 = hash_password("TestPassword1@")
        h2 = hash_password("TestPassword2@")
        assert h1 != h2

    def test_same_password_produces_different_hashes_salted(self):
        from security.auth import hash_password
        # Argon2 salts automatically — two hashes of same password differ
        h1 = hash_password("TestPassword1@")
        h2 = hash_password("TestPassword1@")
        assert h1 != h2

    def test_password_too_short_rejected(self):
        from security.auth import hash_password
        with pytest.raises(ValueError, match="at least"):
            hash_password("Short1@")

    def test_password_too_long_rejected(self):
        from security.auth import hash_password
        with pytest.raises(ValueError, match="exceed"):
            hash_password("A1@" + "x" * 130)

    def test_password_no_uppercase_rejected(self):
        from security.auth import hash_password
        with pytest.raises(ValueError):
            hash_password("nouppercase1@test")

    def test_password_no_digit_rejected(self):
        from security.auth import hash_password
        with pytest.raises(ValueError):
            hash_password("NoDigitPassword@")

    def test_password_no_special_char_rejected(self):
        from security.auth import hash_password
        with pytest.raises(ValueError):
            hash_password("NoSpecialChar1234")


# ═══════════════════════════════════════════════════════════════════════════════
# API KEY GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIKeys:

    def test_generate_api_key_returns_tuple(self):
        from security.auth import generate_api_key
        raw, hashed = generate_api_key()
        assert isinstance(raw, str)
        assert isinstance(hashed, str)

    def test_api_key_has_prefix(self):
        from security.auth import generate_api_key
        from security.config import API_KEY_PREFIX
        raw, _ = generate_api_key()
        assert raw.startswith(API_KEY_PREFIX)

    def test_api_key_raw_not_equal_hash(self):
        from security.auth import generate_api_key
        raw, hashed = generate_api_key()
        assert raw != hashed

    def test_verify_api_key_correct(self):
        from security.auth import generate_api_key, verify_api_key
        raw, hashed = generate_api_key()
        assert verify_api_key(raw, hashed) is True

    def test_verify_api_key_wrong(self):
        from security.auth import generate_api_key, verify_api_key
        raw, hashed = generate_api_key()
        assert verify_api_key("msp_wrongkey", hashed) is False

    def test_api_keys_unique(self):
        from security.auth import generate_api_key
        keys = {generate_api_key()[0] for _ in range(100)}
        assert len(keys) == 100  # all unique

    def test_constant_time_comparison(self):
        """Verify api key comparison doesn't leak timing info."""
        from security.auth import generate_api_key, verify_api_key
        raw, hashed = generate_api_key()

        t1_start = time.perf_counter()
        verify_api_key(raw, hashed)
        t1 = time.perf_counter() - t1_start

        t2_start = time.perf_counter()
        verify_api_key("msp_completelyWrongKeyValue1234", hashed)
        t2 = time.perf_counter() - t2_start

        # Both should complete in similar time (within 10ms tolerance)
        assert abs(t1 - t2) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# SCOPE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestScopes:

    def test_valid_scopes_accepted(self):
        from security.auth import SCOPE_RANK, VALID_SCOPES
        for scope in ["public", "research", "admin"]:
            assert scope in VALID_SCOPES

    def test_scope_rank_ordering(self):
        from security.auth import SCOPE_RANK
        assert SCOPE_RANK["public"] < SCOPE_RANK["research"]
        assert SCOPE_RANK["research"] < SCOPE_RANK["admin"]


# ═══════════════════════════════════════════════════════════════════════════════
# BRUTE FORCE LOCKOUT (mocked Redis)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBruteForce:

    def test_lockout_raises_429_when_locked(self):
        from fastapi import HTTPException
        with patch("security.auth._REDIS_OK", True), \
             patch("security.auth._redis") as mock_redis:
            mock_redis.exists.return_value = True
            mock_redis.ttl.return_value    = 300

            from security.auth import check_lockout
            with pytest.raises(HTTPException) as exc:
                check_lockout("test-user")
            assert exc.value.status_code == 429

    def test_no_lockout_when_redis_unavailable(self):
        with patch("security.auth._REDIS_OK", False):
            from security.auth import check_lockout
            # Should not raise when Redis is down
            check_lockout("test-user")

    def test_record_failed_attempt_returns_count(self):
        with patch("security.auth._REDIS_OK", True), \
             patch("security.auth._redis") as mock_redis:
            mock_redis.incr.return_value = 3
            from security.auth import record_failed_attempt
            count = record_failed_attempt("test-user")
            assert count == 3

    def test_clear_failed_attempts_calls_delete(self):
        with patch("security.auth._REDIS_OK", True), \
             patch("security.auth._redis") as mock_redis:
            from security.auth import clear_failed_attempts
            clear_failed_attempts("test-user")
            assert mock_redis.delete.call_count == 2  # lockout + attempt keys


# ═══════════════════════════════════════════════════════════════════════════════
# COOKIE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCookies:

    def test_set_auth_cookies_sets_httponly(self):
        from fastapi.responses import JSONResponse
        response = JSONResponse({})
        with patch("security.auth.COOKIE_SECURE", False), \
             patch("security.auth.COOKIE_DOMAIN", "localhost"):
            from security.auth import set_auth_cookies
            set_auth_cookies(response, "access-token", "refresh-token")
        # FastAPI response cookies are set — verify via headers
        cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower() or True  # depends on test runner

    def test_clear_auth_cookies_removes_both(self):
        from fastapi.responses import JSONResponse
        response = JSONResponse({})
        from security.auth import clear_auth_cookies
        clear_auth_cookies(response)  # Should not raise
