import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from security.audit import log_api_call, log_auth_event, log_security_event, verify_audit_log, _sanitize_params

def test_sanitize_params():
    params = {"password": "secret_password", "token": "abc", "safe_key": "safe_value"}
    sanitized = _sanitize_params(params)
    assert sanitized["password"] == "***"
    assert sanitized["token"] == "***"
    assert sanitized["safe_key"] == "safe_value"

def test_audit_logging():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "audit.log")
        
        with patch("security.audit.AUDIT_LOG_PATH", log_path):
            log_api_call("user1", "/test", "GET", {"a": 1}, 200, 10.5, "hash123", "SELECT 1")
            log_auth_event("login_success", "user1", "hash123", "details")
            log_security_event("test_event", "user1", "hash123", "low", {"k": "v"})
            
            result = verify_audit_log(log_path)
            assert result["total"] == 3
            assert result["valid"] == 3
            assert result["tampered"] == 0
            assert result["unreadable"] == 0
            assert result["integrity"] is True

            # Test tampering
            with open(log_path, "a", encoding="utf-8") as f:
                f.write('{"tampered": "yes"}\n')
                f.write('not-json\n')
            
            result = verify_audit_log(log_path)
            assert result["total"] == 5
            assert result["valid"] == 3
            assert result["tampered"] == 1
            assert result["unreadable"] == 1
            assert result["integrity"] is False
