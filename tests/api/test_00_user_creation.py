# tests/api/test_users.py
from __future__ import annotations

import time

import jwt

from sports_tracker.settings import settings


def _auth_headers(client, email: str, password: str = "supersecret1") -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_user_ok(client):
    r = client.post(
        "/api/v1/users", json={"email": "test@example.com", "password": "supersecret1"}
    )
    assert r.status_code == 201, r.text

    data = r.json()
    assert "id" in data
    assert data["email"] == "test@example.com"
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_create_user_invalid_email_422(client):
    r = client.post(
        "/api/v1/users", json={"email": "not-an-email", "password": "supersecret1"}
    )
    assert r.status_code == 422, r.text


def test_create_user_short_password_422(client):
    r = client.post(
        "/api/v1/users", json={"email": "shortpw@example.com", "password": "short"}
    )
    assert r.status_code == 422, r.text


def test_create_user_duplicate_409(client):
    r1 = client.post(
        "/api/v1/users", json={"email": "dup@example.com", "password": "supersecret1"}
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/api/v1/users", json={"email": "dup@example.com", "password": "supersecret1"}
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"] == "User with this email already exists"


def test_login_ok(client):
    client.post(
        "/api/v1/users", json={"email": "login@example.com", "password": "supersecret1"}
    )

    r = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_401(client):
    client.post(
        "/api/v1/users", json={"email": "wrongpw@example.com", "password": "supersecret1"}
    )

    r = client.post(
        "/api/v1/auth/login",
        data={"username": "wrongpw@example.com", "password": "nope"},
    )
    assert r.status_code == 401, r.text


def test_login_remember_me_token_expiry(client):
    client.post(
        "/api/v1/users", json={"email": "remember@example.com", "password": "supersecret1"}
    )

    r_remember = client.post(
        "/api/v1/auth/login",
        data={
            "username": "remember@example.com",
            "password": "supersecret1",
            "remember_me": "true",
        },
    )
    assert r_remember.status_code == 200, r_remember.text

    r_session = client.post(
        "/api/v1/auth/login",
        data={
            "username": "remember@example.com",
            "password": "supersecret1",
            "remember_me": "false",
        },
    )
    assert r_session.status_code == 200, r_session.text

    def _lifetime_seconds(token: str) -> float:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return payload["exp"] - time.time()

    remember_lifetime = _lifetime_seconds(r_remember.json()["access_token"])
    session_lifetime = _lifetime_seconds(r_session.json()["access_token"])

    # Remembered logins last REMEMBER_ME_EXPIRE_DAYS; plain logins keep the
    # ACCESS_TOKEN_EXPIRE_MINUTES window. Generous tolerance for token-creation drift.
    assert abs(remember_lifetime - settings.REMEMBER_ME_EXPIRE_DAYS * 86400) < 120
    assert abs(session_lifetime - settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) < 120
    assert remember_lifetime > session_lifetime


def test_get_user_ok(client):
    r1 = client.post(
        "/api/v1/users", json={"email": "getme@example.com", "password": "supersecret1"}
    )
    assert r1.status_code == 201, r1.text
    user_id = r1.json()["id"]

    headers = _auth_headers(client, "getme@example.com")
    r2 = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["id"] == user_id
    assert data["email"] == "getme@example.com"
    assert "created_at" in data


def test_get_user_requires_auth_401(client):
    r1 = client.post(
        "/api/v1/users", json={"email": "noauth@example.com", "password": "supersecret1"}
    )
    user_id = r1.json()["id"]

    r2 = client.get(f"/api/v1/users/{user_id}")
    assert r2.status_code == 401, r2.text


def test_get_user_not_found_404(client):
    client.post(
        "/api/v1/users", json={"email": "lookup@example.com", "password": "supersecret1"}
    )
    headers = _auth_headers(client, "lookup@example.com")
    r = client.get("/api/v1/users/999999", headers=headers)
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "User not found"


def test_get_current_user_me_ok(client):
    client.post(
        "/api/v1/users", json={"email": "me@example.com", "password": "supersecret1"}
    )
    headers = _auth_headers(client, "me@example.com")

    r = client.get("/api/v1/users/me", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "me@example.com"
