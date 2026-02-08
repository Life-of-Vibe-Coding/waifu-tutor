from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_contracts() -> None:
    payload = {"email": "demo@waifu.local", "password": "demo"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["profile"]["id"] == "demo-user"


def test_profile() -> None:
    response = client.get("/api/user/profile")
    assert response.status_code == 200
    assert response.json()["email"] == "demo@waifu.local"
