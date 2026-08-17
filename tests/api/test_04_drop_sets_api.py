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


def _create_session(client, headers, exercise_id: int, n: int = 2) -> dict:
    sets = [{"exercise_id": exercise_id, "reps": 10, "weight": 50.0} for _ in range(n)]
    r = client.post(
        "/api/v1/sessions",
        json={"name": "Workout", "workout_sets": sets},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_workout_set_endpoints_require_auth(client):
    assert (
        client.post(
            "/api/v1/sessions/1/workout-sets",
            json={"exercise_id": 1, "reps": 10, "weight": 50.0},
        ).status_code
        == 401
    )
    assert (
        client.put(
            "/api/v1/sessions/1/workout-sets/order",
            json={"set_ids": [1, 2]},
        ).status_code
        == 401
    )


def test_session_create_assigns_default_position_and_set_type(client):
    _create_user(client, "drop1@example.com")
    headers = _auth_headers(client, "drop1@example.com")
    exercise = _create_exercise(client, headers, "Bench Press")

    r = client.post(
        "/api/v1/sessions",
        json={
            "name": "Chest",
            "workout_sets": [
                {"exercise_id": exercise["id"], "reps": 10, "weight": 50.0},
                {"exercise_id": exercise["id"], "reps": 8, "weight": 55.0, "set_type": "drop"},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    sets = r.json()["workout_sets"]
    assert [s["position"] for s in sets] == [0, 1]
    assert sets[0]["set_type"] == "normal"
    assert sets[1]["set_type"] == "drop"


def test_add_workout_set_appends_at_end(client):
    _create_user(client, "drop2@example.com")
    headers = _auth_headers(client, "drop2@example.com")
    exercise = _create_exercise(client, headers, "Pull-Up")
    session = _create_session(client, headers, exercise["id"], n=2)
    session_id = session["id"]

    r = client.post(
        f"/api/v1/sessions/{session_id}/workout-sets",
        json={"exercise_id": exercise["id"], "reps": 6, "weight": 0, "set_type": "drop"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["position"] == 2

    r = client.post(
        f"/api/v1/sessions/{session_id}/workout-sets",
        json={"exercise_id": 9999, "reps": 6, "weight": 0},
        headers=headers,
    )
    assert r.status_code == 404, r.text


def test_add_workout_set_with_position_shifts_existing(client):
    _create_user(client, "drop3@example.com")
    headers = _auth_headers(client, "drop3@example.com")
    exercise = _create_exercise(client, headers, "Barbell Squat")
    session = _create_session(client, headers, exercise["id"], n=2)
    session_id = session["id"]

    r = client.post(
        f"/api/v1/sessions/{session_id}/workout-sets",
        json={"exercise_id": exercise["id"], "reps": 5, "weight": 100.0, "position": 1},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["position"] == 1

    sets = client.get(f"/api/v1/sessions/{session_id}", headers=headers).json()["workout_sets"]
    assert [s["position"] for s in sets] == [0, 1, 2]


def test_update_workout_set_position_and_type(client):
    _create_user(client, "drop4@example.com")
    headers = _auth_headers(client, "drop4@example.com")
    exercise = _create_exercise(client, headers, "Bench Press")
    session = _create_session(client, headers, exercise["id"], n=1)
    session_id = session["id"]
    set_id = session["workout_sets"][0]["id"]

    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"set_type": "drop", "weight": 60.0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["set_type"] == "drop"
    assert r.json()["weight"] == 60.0


def test_reorder_workout_sets(client):
    _create_user(client, "drop5@example.com")
    headers = _auth_headers(client, "drop5@example.com")
    exercise = _create_exercise(client, headers, "Pull-Up")
    session = _create_session(client, headers, exercise["id"], n=3)
    session_id = session["id"]
    ids = [s["id"] for s in session["workout_sets"]]

    r = client.put(
        f"/api/v1/sessions/{session_id}/workout-sets/order",
        json={"set_ids": list(reversed(ids))},
        headers=headers,
    )
    assert r.status_code == 204, r.text

    sets = client.get(f"/api/v1/sessions/{session_id}", headers=headers).json()["workout_sets"]
    assert [s["id"] for s in sets] == list(reversed(ids))
    assert [s["position"] for s in sets] == [0, 1, 2]

    # A partial list is rejected.
    r = client.put(
        f"/api/v1/sessions/{session_id}/workout-sets/order",
        json={"set_ids": ids[:2]},
        headers=headers,
    )
    assert r.status_code == 422, r.text

    # Duplicate ids are rejected.
    r = client.put(
        f"/api/v1/sessions/{session_id}/workout-sets/order",
        json={"set_ids": [ids[0], ids[0], ids[1]]},
        headers=headers,
    )
    assert r.status_code == 422, r.text
