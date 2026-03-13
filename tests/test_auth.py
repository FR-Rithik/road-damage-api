def test_missing_key(client):
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_missing_key_has_detail(client):
    response = client.get("/auth/me")
    assert "detail" in response.json()

def test_invalid_key(client):
    response = client.get("/auth/me", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403

def test_inactive_key(client):
    response = client.get("/auth/me", headers={"X-API-Key": "inactive-key-123"})
    assert response.status_code == 403

def test_valid_key(client):
    response = client.get("/auth/me", headers={"X-API-Key": "valid-key-123"})
    assert response.status_code == 200

def test_valid_key_returns_correct_fields(client):
    response = client.get("/auth/me", headers={"X-API-Key": "valid-key-123"})
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["is_active"] == True
    assert "id" in data
    assert "created_at" in data