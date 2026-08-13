from __future__ import annotations

from sports_tracker.db.models.muscle import Muscle
from sports_tracker.db.models.exercise import Exercise


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
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_muscle(db_session, name: str) -> Muscle:
    muscle = Muscle(name=name)
    db_session.add(muscle)
    db_session.commit()
    db_session.refresh(muscle)
    return muscle


def _create_exercise(client, headers, name: str, muscle_ids: list[int] | None = None) -> dict:
    r = client.post(
        "/api/v1/exercises",
        json={"name": name, "muscle_ids": muscle_ids or []},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_list_muscles_and_exercises_require_auth(client):
    assert client.get("/api/v1/exercises").status_code == 401
    assert client.get("/api/v1/muscles").status_code == 401


def test_create_exercise_with_muscles(client, db_session):
    _create_user(client, "exercise@example.com")
    headers = _auth_headers(client, "exercise@example.com")
    quad = _create_muscle(db_session, "Quadriceps")
    ham = _create_muscle(db_session, "Hamstrings")

    exercise = _create_exercise(client, headers, "Barbell Squat", [quad.id, ham.id])

    assert exercise["name"] == "Barbell Squat"
    assert {m["name"] for m in exercise["muscles"]} == {"Quadriceps", "Hamstrings"}


def test_create_exercise_duplicate_409(client):
    _create_user(client, "dupex@example.com")
    headers = _auth_headers(client, "dupex@example.com")
    _create_exercise(client, headers, "Bench Press")

    r = client.post("/api/v1/exercises", json={"name": "Bench Press", "muscle_ids": []}, headers=headers)
    assert r.status_code == 409, r.text


def test_create_exercise_unknown_muscle_404(client):
    _create_user(client, "badmuscle@example.com")
    headers = _auth_headers(client, "badmuscle@example.com")

    r = client.post("/api/v1/exercises", json={"name": "Mystery Move", "muscle_ids": [9999]}, headers=headers)
    assert r.status_code == 404, r.text


def test_list_exercises(client, db_session):
    _create_user(client, "listex@example.com")
    headers = _auth_headers(client, "listex@example.com")
    chest = _create_muscle(db_session, "Chest")
    _create_exercise(client, headers, "Bench Press", [chest.id])

    r = client.get("/api/v1/exercises", headers=headers)
    assert r.status_code == 200
    names = [e["name"] for e in r.json()]
    assert "Bench Press" in names


def test_create_session_with_workout_sets(client, db_session):
    _create_user(client, "sess@example.com")
    headers = _auth_headers(client, "sess@example.com")
    quad = _create_muscle(db_session, "Quadriceps")
    exercise = _create_exercise(client, headers, "Quadriceps Extension", [quad.id])

    r = client.post(
        "/api/v1/sessions",
        json={
            "name": "Leg Day",
            "workout_sets": [
                {"exercise_id": exercise["id"], "reps": 12, "weight": 60.0},
                {"exercise_id": exercise["id"], "reps": 10, "weight": 65.0},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Leg Day"
    assert data["user_id"] > 0

    sets = data["workout_sets"]
    assert len(sets) == 2
    assert sets[0]["reps"] == 12
    assert sets[0]["weight"] == 60.0
    assert sets[0]["exercise_name"] == "Quadriceps Extension"
    assert sets[0]["session_id"] == data["id"]


def test_create_session_unknown_exercise_404(client):
    _create_user(client, "badex@example.com")
    headers = _auth_headers(client, "badex@example.com")

    r = client.post(
        "/api/v1/sessions",
        json={"name": "Leg Day", "workout_sets": [{"exercise_id": 9999, "reps": 10, "weight": 0}]},
        headers=headers,
    )
    assert r.status_code == 404, r.text


def test_sessions_are_private_per_user(client, db_session):
    _create_user(client, "alice@example.com")
    alice_headers = _auth_headers(client, "alice@example.com")

    _create_user(client, "bob@example.com")
    bob_headers = _auth_headers(client, "bob@example.com")

    exercise = _create_exercise(client, alice_headers, "Pull-Up", [])
    r = client.post(
        "/api/v1/sessions",
        json={"name": "Alice Push", "workout_sets": [{"exercise_id": exercise["id"], "reps": 8, "weight": 0}]},
        headers=alice_headers,
    )
    assert r.status_code == 201, r.text
    session_id = r.json()["id"]

    # Bob cannot see or touch Alice's session
    assert client.get(f"/api/v1/sessions/{session_id}", headers=bob_headers).status_code == 404
    assert client.delete(f"/api/v1/sessions/{session_id}", headers=bob_headers).status_code == 404

    # Bob's own list is empty
    r = client.get("/api/v1/sessions", headers=bob_headers)
    assert r.status_code == 200
    assert r.json() == []

    # Alice's list contains her session
    r = client.get("/api/v1/sessions", headers=alice_headers)
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [session_id]


def test_update_workout_set(client, db_session):
    _create_user(client, "update@example.com")
    headers = _auth_headers(client, "update@example.com")
    exercise = _create_exercise(client, headers, "Bench Press", [])
    r = client.post(
        "/api/v1/sessions",
        json={"name": "Chest", "workout_sets": [{"exercise_id": exercise["id"], "reps": 10, "weight": 50.0}]},
        headers=headers,
    )
    session_id = r.json()["id"]
    set_id = r.json()["workout_sets"][0]["id"]

    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"reps": 12, "weight": 55.0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["reps"] == 12
    assert r.json()["weight"] == 55.0

    # Partial update: only weight
    r = client.patch(
        f"/api/v1/sessions/{session_id}/workout-sets/{set_id}",
        json={"weight": 60.0},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["reps"] == 12
    assert r.json()["weight"] == 60.0


def test_delete_workout_set(client, db_session):
    _create_user(client, "delset@example.com")
    headers = _auth_headers(client, "delset@example.com")
    exercise = _create_exercise(client, headers, "Pull-Up", [])
    r = client.post(
        "/api/v1/sessions",
        json={
            "name": "Back",
            "workout_sets": [
                {"exercise_id": exercise["id"], "reps": 8, "weight": 0},
                {"exercise_id": exercise["id"], "reps": 6, "weight": 5},
            ],
        },
        headers=headers,
    )
    session_id = r.json()["id"]
    set_ids = [s["id"] for s in r.json()["workout_sets"]]

    r = client.delete(f"/api/v1/sessions/{session_id}/workout-sets/{set_ids[0]}", headers=headers)
    assert r.status_code == 204, r.text

    r = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert [s["id"] for s in r.json()["workout_sets"]] == [set_ids[1]]

    # Deleting the same set again -> 404
    r = client.delete(f"/api/v1/sessions/{session_id}/workout-sets/{set_ids[0]}", headers=headers)
    assert r.status_code == 404, r.text


def test_delete_session_cascades_to_sets(client, db_session):
    _create_user(client, "delsess@example.com")
    headers = _auth_headers(client, "delsess@example.com")
    exercise = _create_exercise(client, headers, "Barbell Squat", [])
    r = client.post(
        "/api/v1/sessions",
        json={"name": "Leg Day", "workout_sets": [{"exercise_id": exercise["id"], "reps": 5, "weight": 100}]},
        headers=headers,
    )
    session_id = r.json()["id"]

    r = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert r.status_code == 204, r.text

    assert client.get(f"/api/v1/sessions/{session_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/sessions", headers=headers).json() == []
