ADMIN_KEY = "supersecretadminkey"


def test_create_key_as_admin(client):
    response = client.post("/auth/keys?name=testclient", headers={"X-API-Key": ADMIN_KEY})
    assert response.status_code == 201
    data = response.json()
    assert "key" in data
    assert data["name"] == "testclient"
    assert "note" in data


def test_create_key_without_admin_key(client):
    response = client.post("/auth/keys?name=testclient")
    assert response.status_code == 403


def test_use_created_key_on_me(client):
    create = client.post("/auth/keys?name=myclient", headers={"X-API-Key": ADMIN_KEY})
    raw_key = create.json()["key"]

    response = client.get("/auth/me", headers={"X-API-Key": raw_key})
    assert response.status_code == 200
    assert response.json()["name"] == "myclient"


def test_revoke_key_blocks_access(client):
    create = client.post("/auth/keys?name=tobedeleted", headers={"X-API-Key": ADMIN_KEY})
    data = create.json()
    raw_key = data["key"]
    client_id = data["id"]

    response = client.get("/auth/me", headers={"X-API-Key": raw_key})
    assert response.status_code == 200

    revoke = client.delete(f"/auth/keys/{client_id}", headers={"X-API-Key": ADMIN_KEY})
    assert revoke.status_code == 200

    response = client.get("/auth/me", headers={"X-API-Key": raw_key})
    assert response.status_code == 403