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


def _create_exercise(client, headers, name: str) -> dict:
    r = client.post(
        "/api/v1/exercises",
        json={"name": name, "muscle_ids": []},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_session(client, headers, exercise_id: int, n: int = 1) -> dict:
    sets = [{"exercise_id": exercise_id, "reps": 10, "weight": 50.0} for _ in range(n)]
    r = client.post(
        "/api/v1/sessions",
        json={"name": "Workout", "workout_sets": sets},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_session_with_superset_group(client):
    _create_user(client, "ss1@example.com")
    headers = _auth_headers(client, "ss1@example.com")
    bench = _create_exercise(client, headers, "Bench Press")
    row = _create_exercise(client, headers, "Barbell Row")
    group = "abc-123-def"

    r = client.post(
        "/api/v1/sessions",
        json={
            "name": "Upper",
            "workout_sets": [
                {"exercise_id": bench["id"], "reps": 10, "weight": 60.0, "superset_group": group},
                {"exercise_id": row["id"], "reps": 10, "weight": 40.0, "superset_group": group},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    sets = r.json()["workout_sets"]
    assert sets[0]["superset_group"] == group
    assert sets[1]["superset_group"] == group


def test_patch_superset_group_add_and_clear(client):
    _create_user(client, "ss2@example.com")
    headers = _auth_headers(client, "ss2@example.com")
    bench = _create_exercise(client, headers, "Bench Press")
    session = _create_session(client, headers, bench["id"], n=1)
    session_id = session["id"]
    set_id = session["workout_sets"][0]["id"]

    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"superset_group": "grp-1"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["superset_group"] == "grp-1"

    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"superset_group": None},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["superset_group"] is None


def test_reorder_preserves_superset_groups(client):
    _create_user(client, "ss3@example.com")
    headers = _auth_headers(client, "ss3@example.com")
    bench = _create_exercise(client, headers, "Bench Press")
    row = _create_exercise(client, headers, "Barbell Row")
    group = "grp-xyz"

    r = client.post(
        "/api/v1/sessions",
        json={
            "name": "Upper",
            "workout_sets": [
                {"exercise_id": bench["id"], "reps": 10, "weight": 60.0, "superset_group": group},
                {"exercise_id": row["id"], "reps": 10, "weight": 40.0, "superset_group": group},
                {"exercise_id": bench["id"], "reps": 8, "weight": 65.0},
            ],
        },
        headers=headers,
    )
    session = r.json()
    session_id = session["id"]
    ids = [s["id"] for s in session["workout_sets"]]

    r = client.put(
        f"/api/v1/sessions/{session_id}/workout-sets/order",
        json={"set_ids": list(reversed(ids))},
        headers=headers,
    )
    assert r.status_code == 204, r.text

    sets = client.get(f"/api/v1/sessions/{session_id}", headers=headers).json()["workout_sets"]
    by_id = {s["id"]: s for s in sets}
    assert by_id[ids[0]]["superset_group"] == group
    assert by_id[ids[1]]["superset_group"] == group
    assert by_id[ids[2]]["superset_group"] is None


def test_superset_member_isolation(client):
    _create_user(client, "ss4@example.com")
    headers = _auth_headers(client, "ss4@example.com")
    _create_user(client, "ss5@example.com")
    other = _auth_headers(client, "ss5@example.com")

    bench = _create_exercise(client, headers, "Bench Press")
    session = _create_session(client, headers, bench["id"], n=1)
    session_id = session["id"]
    set_id = session["workout_sets"][0]["id"]

    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"superset_group": "grp"},
        headers=other,
    )
    assert r.status_code == 404, r.text
    r = client.delete(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}", headers=other
    )
    assert r.status_code == 404, r.text
