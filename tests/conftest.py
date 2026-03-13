import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import ApiClient, Base

TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
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
    active_client = ApiClient(name="Test Client", key_hash=hashed, is_active=True)

    hashed_inactive = hashlib.sha256("inactive-key-123".encode()).hexdigest()
    inactive_client = ApiClient(name="Inactive Client", key_hash=hashed_inactive, is_active=False)

    db.add(active_client)
    db.add(inactive_client)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
