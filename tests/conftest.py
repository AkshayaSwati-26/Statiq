# tests/conftest.py
# Shared pytest fixtures and configuration.

import os
import pytest

# Set all test environment variables before any imports
os.environ.setdefault("FORCE_HTTPS",           "false")
os.environ.setdefault("JWT_SECRET",            "test-secret-at-least-32-chars-long!!")
os.environ.setdefault("RSA_PRIVATE_KEY_PATH",  "keys/private.pem")
os.environ.setdefault("RSA_PUBLIC_KEY_PATH",   "keys/public.pem")
os.environ.setdefault("REDIS_URL",             "redis://localhost:6379/0")
os.environ.setdefault("ALLOWED_ORIGINS",       "http://localhost:5173")
os.environ.setdefault("ALLOWED_HOSTS",         "*")
os.environ.setdefault("COOKIE_DOMAIN",         "testserver")
os.environ.setdefault("AUDIT_LOG_PATH",        "/tmp/mospi_test_audit.jsonl")
os.environ.setdefault("DATABASE_URL",          "sqlite:///:memory:")
