import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db
from app.models import Base, ApiClient

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
    hashed = hashlib.sha256("valid-key-123".encode()).hexdigest()
    client = ApiClient(name="Test Client", key_hash=hashed, is_active=True)
    db.add(client)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_missing_key():
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_invalid_key():
    response = client.get("/auth/me", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

def test_valid_key():
    response = client.get("/auth/me", headers={"X-API-Key": "valid-key-123"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["is_active"] == True

