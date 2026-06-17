import os
import importlib

# Ensure DATABASE_URL is set to postgres for this integration test
db_url = os.environ.get("DATABASE_URL", "")
if not db_url or "sqlite" in db_url.lower():
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://statiq:statiq123@127.0.0.1:5434/statiq"

# Force reload of db.postgres_client and db.loader to use the Postgres database URL
try:
    import db.postgres_client
    importlib.reload(db.postgres_client)
    import db.loader
    importlib.reload(db.loader)
except ImportError:
    pass

import pytest
import pytest_asyncio
import pandas as pd
import io
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

@pytest.fixture(scope="session")
def app():
    from api.main import app
    return app

@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def auth_headers():
    from security.auth import create_access_token
    token = create_access_token("analyst", "research")
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def admin_headers():
    from security.auth import create_access_token
    token = create_access_token("admin", "admin")
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def public_headers():
    from security.auth import create_access_token
    token = create_access_token("student", "public")
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_dynamic_csv_upload_flow(client, admin_headers):
    # Retrieve the database engine
    from db.loader import engine

    # Ensure no previous test state exists
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS employment_dataset CASCADE"))
        conn.execute(text("DELETE FROM survey_metadata_columns WHERE table_name = 'employment_dataset'"))
        conn.execute(text("DELETE FROM survey_metadata_samples WHERE table_name = 'employment_dataset'"))
        conn.execute(text("DELETE FROM survey_metadata_profiles WHERE table_name = 'employment_dataset'"))

    # 1. Create a dummy CSV DataFrame
    df = pd.DataFrame({
        "state": ["Tamil Nadu", "Karnataka", "Maharashtra"],
        "employment_rate": [0.92, 0.91, 0.95],
        "respondents": [1200, 1100, 1500]
    })
    
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    files = {"file": ("employment_dataset.csv", csv_buffer, "text/csv")}
    
    # 2. Upload the CSV file - must fail if not admin
    resp = await client.post("/upload", files=files)
    assert resp.status_code == 401 # Unauthenticated

    # Upload with admin headers - returns 400 since manual ingestion is disabled
    resp = await client.post("/upload", files=files, headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Manual ingestion is disabled."


@pytest.mark.asyncio
async def test_virtual_upload_flow(client, auth_headers, public_headers):
    # Test virtual HCES load - Free user (public) must get 403
    files = {"file": ("hces.csv", b"", "text/csv")}
    resp = await client.post("/upload", files=files, headers=public_headers)
    assert resp.status_code == 403

    # Premium/Research user must succeed
    resp = await client.post("/upload", files=files, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["dataset_id"] == "api_hces_members"
    assert "preview_rows" in data

    # Test virtual PLFS load - Free/Public user must succeed
    files = {"file": ("plfs.csv", b"", "text/csv")}
    resp = await client.post("/upload", files=files, headers=public_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["dataset_id"] == "api_plfs_person"
    assert "preview_rows" in data
