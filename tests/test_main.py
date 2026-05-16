def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_not_found_handler(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}
