from fastapi.testclient import TestClient
from api.main import app
import pytest

client = TestClient(app)

def test_nl_query_missing_auth():
    response = client.post("/v1/query/nl", json={"question": "what is unemployment"})
    assert response.status_code == 401

def test_direct_sql_missing_auth():
    response = client.post("/v1/query/sql", json={"sql": "SELECT 1", "reason": "test access reason for sql endpoint"})
    assert response.status_code == 401

def test_query_history_missing_auth():
    response = client.get("/v1/query/history")
    assert response.status_code == 401

def test_nl_query_invalid_lang():
    response = client.post("/v1/query/nl", json={"question": "what is unemployment", "language": "xx"})
    # Since auth is first, we expect 401. If we bypass auth, we'd test logic.
    assert response.status_code == 401
