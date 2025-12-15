# tests/api/test_users.py
from __future__ import annotations


def test_create_user_ok(client):
    r = client.post("/api/v1/users", json={"email": "test@example.com"})
    assert r.status_code == 201, r.text

    data = r.json()
    assert "id" in data
    assert data["email"] == "test@example.com"
    assert "created_at" in data


def test_create_user_invalid_email_422(client):
    r = client.post("/api/v1/users", json={"email": "not-an-email"})
    assert r.status_code == 422, r.text


def test_create_user_duplicate_409(client):
    r1 = client.post("/api/v1/users", json={"email": "dup@example.com"})
    assert r1.status_code == 201, r1.text

    r2 = client.post("/api/v1/users", json={"email": "dup@example.com"})
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"] == "User with this email already exists"


def test_get_user_ok(client):
    r1 = client.post("/api/v1/users", json={"email": "getme@example.com"})
    assert r1.status_code == 201, r1.text
    user_id = r1.json()["id"]

    r2 = client.get(f"/api/v1/users/{user_id}")
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["id"] == user_id
    assert data["email"] == "getme@example.com"
    assert "created_at" in data


def test_get_user_not_found_404(client):
    r = client.get("/api/v1/users/999999")
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "User not found"
