from __future__ import annotations


def _create_user(client, email: str, password: str = "supersecret1") -> dict:
    r = client.post("/api/v1/users", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def _auth_headers(client, email: str, password: str = "supersecret1") -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post_measurement(client, headers, date_: str, weight=None, waist=None) -> dict:
    body = {"date": date_}
    if weight is not None:
        body["weight_kg"] = weight
    if waist is not None:
        body["waist_cm"] = waist
    r = client.post("/api/v1/measurements", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_measurements_require_auth(client):
    assert client.get("/api/v1/measurements").status_code == 401
    assert client.get("/api/v1/measurements/series").status_code == 401
    assert client.get("/api/v1/settings").status_code == 401
    assert (
        client.post(
            "/api/v1/measurements",
            json={"date": "2026-08-01", "weight_kg": 70.0},
        ).status_code
        == 401
    )
    assert client.patch("/api/v1/measurements/1", json={"weight_kg": 70.0}).status_code == 401
    assert client.patch("/api/v1/settings", json={"weight_ma_window": 14}).status_code == 401


def test_upsert_measurement(client):
    _create_user(client, "meas@example.com")
    headers = _auth_headers(client, "meas@example.com")

    first = _post_measurement(client, headers, "2026-08-01", weight=70.0)
    second = _post_measurement(client, headers, "2026-08-01", weight=71.0)
    assert first["id"] == second["id"]

    rows = client.get("/api/v1/measurements", headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["weight_kg"] == 71.0
    assert rows[0]["waist_cm"] is None

    # Logging waist only on the same day preserves the existing weight.
    _post_measurement(client, headers, "2026-08-01", waist=80.0)
    rows = client.get("/api/v1/measurements", headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["weight_kg"] == 71.0
    assert rows[0]["waist_cm"] == 80.0


def test_measurements_are_private_per_user(client):
    _create_user(client, "alice@example.com")
    alice = _auth_headers(client, "alice@example.com")
    _create_user(client, "bob@example.com")
    bob = _auth_headers(client, "bob@example.com")

    _post_measurement(client, alice, "2026-08-01", weight=70.0)

    assert client.get("/api/v1/measurements", headers=bob).json() == []

    measurement_id = client.get("/api/v1/measurements", headers=alice).json()[0]["id"]
    assert (
        client.patch(
            f"/api/v1/measurements/{measurement_id}",
            json={"weight_kg": 72.0},
            headers=bob,
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/measurements/{measurement_id}", headers=bob).status_code
        == 404
    )


def test_weight_only_does_not_affect_waist_series(client):
    _create_user(client, "wonly@example.com")
    headers = _auth_headers(client, "wonly@example.com")

    _post_measurement(client, headers, "2026-08-01", weight=70.0)
    _post_measurement(client, headers, "2026-08-02", weight=72.0)

    points = client.get("/api/v1/measurements/series", headers=headers).json()
    assert points[-1]["weight_ma"] == 71.0
    assert points[-1]["waist_cm"] is None
    assert points[-1]["waist_ma"] is None


def test_series_moving_average_and_override(client):
    _create_user(client, "series@example.com")
    headers = _auth_headers(client, "series@example.com")

    weights = [70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0]
    for i, w in enumerate(weights, start=1):
        _post_measurement(client, headers, f"2026-08-{i:02d}", weight=w)

    # Default saved window is 7 -> last MA = mean of all 7.
    points = client.get("/api/v1/measurements/series", headers=headers).json()
    assert len(points) == 7
    assert points[-1]["weight_ma"] == 73.0

    # Per-request override beats the saved window.
    points = client.get(
        "/api/v1/measurements/series?weight_window=3", headers=headers
    ).json()
    assert points[-1]["weight_ma"] == 75.0

    points = client.get(
        "/api/v1/measurements/series?weight_window=2", headers=headers
    ).json()
    assert points[-1]["weight_ma"] == 75.5


def test_settings_defaults_and_patch(client):
    _create_user(client, "settings@example.com")
    headers = _auth_headers(client, "settings@example.com")

    r = client.get("/api/v1/settings", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"weight_ma_window": 7, "waist_ma_window": 7}

    r = client.patch(
        "/api/v1/settings", json={"weight_ma_window": 14}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"weight_ma_window": 14, "waist_ma_window": 7}

    # A different user still gets defaults.
    _create_user(client, "settings2@example.com")
    headers2 = _auth_headers(client, "settings2@example.com")
    assert client.get("/api/v1/settings", headers=headers2).json() == {
        "weight_ma_window": 7,
        "waist_ma_window": 7,
    }


def test_delete_measurement(client):
    _create_user(client, "delmeas@example.com")
    headers = _auth_headers(client, "delmeas@example.com")

    measurement = _post_measurement(client, headers, "2026-08-01", weight=70.0)
    measurement_id = measurement["id"]

    r = client.delete(f"/api/v1/measurements/{measurement_id}", headers=headers)
    assert r.status_code == 204, r.text
    assert client.get("/api/v1/measurements", headers=headers).json() == []
    assert (
        client.delete(f"/api/v1/measurements/{measurement_id}", headers=headers).status_code
        == 404
    )


def test_measurement_validation(client):
    _create_user(client, "valid@example.com")
    headers = _auth_headers(client, "valid@example.com")

    # Both metrics missing on create -> 422.
    assert (
        client.post(
            "/api/v1/measurements", json={"date": "2026-08-01"}, headers=headers
        ).status_code
        == 422
    )

    # Negative weight -> 422.
    assert (
        client.post(
            "/api/v1/measurements",
            json={"date": "2026-08-01", "weight_kg": -5},
            headers=headers,
        ).status_code
        == 422
    )

    measurement = _post_measurement(client, headers, "2026-08-02", weight=70.0, waist=80.0)
    measurement_id = measurement["id"]

    # Clearing both metrics via PATCH -> 422.
    assert (
        client.patch(
            f"/api/v1/measurements/{measurement_id}",
            json={"weight_kg": None, "waist_cm": None},
            headers=headers,
        ).status_code
        == 422
    )

    # Empty PATCH body -> 422.
    assert (
        client.patch(
            f"/api/v1/measurements/{measurement_id}", json={}, headers=headers
        ).status_code
        == 422
    )
