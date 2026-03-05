import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import ApiClient, Base

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # active client
    hashed = hashlib.sha256("valid-key-123".encode()).hexdigest()
    active_client = ApiClient(name="Test Client", key_hash=hashed, is_active=True)

    # inactive client
    hashed_inactive = hashlib.sha256("inactive-key-123".encode()).hexdigest()
    inactive_client = ApiClient(name="Inactive Client", key_hash=hashed_inactive, is_active=False)

    db.add(active_client)
    db.add(inactive_client)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

# --- /health tests ---

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200

def test_health_returns_correct_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}

# --- /auth/me tests ---

def test_missing_key():
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_missing_key_has_detail():
    response = client.get("/auth/me")
    assert "detail" in response.json()

def test_invalid_key():
    response = client.get("/auth/me", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

def test_inactive_key():
    response = client.get("/auth/me", headers={"X-API-Key": "inactive-key-123"})
    assert response.status_code == 403

def test_valid_key():
    response = client.get("/auth/me", headers={"X-API-Key": "valid-key-123"})
    assert response.status_code == 200

def test_valid_key_returns_correct_fields():
    response = client.get("/auth/me", headers={"X-API-Key": "valid-key-123"})
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["is_active"] == True
    assert "id" in data
    assert "created_at" in data