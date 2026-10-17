import csv
import io
import pytest
from sports_tracker.db.models.measurement import Measurement


def auth(client, email="improvements@example.com"):
    password = "supersecret1"
    assert client.post("/api/v1/users", json={"email": email, "password": password}).status_code == 201
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def post(client, headers, date, **values):
    response = client.post("/api/v1/measurements", headers=headers, json={"date": date, **values})
    assert response.status_code == 200, response.text
    return response.json()


def test_calendar_windows_and_filtered_warmup(client):
    headers = auth(client)
    post(client, headers, "2026-08-01", weight_kg=100, waist_cm=90)
    post(client, headers, "2026-08-07", weight_kg=80, waist_cm=88)
    post(client, headers, "2026-08-08", weight_kg=70)
    post(client, headers, "2026-08-15", waist_cm=85)
    series = client.get("/api/v1/measurements/series", headers=headers).json()
    assert series[1]["weight_ma"] == 90
    assert series[2]["weight_ma"] == 75
    assert series[2]["weight_count"] == 2
    assert series[2]["waist_ma"] is None  # no fabricated waist average on a weight-only day
    assert series[3]["weight_count"] == 0
    assert series[3]["waist_ma"] == 85
    assert series[3]["waist_count"] == 1
    filtered = client.get("/api/v1/measurements/series?start_date=2026-08-08", headers=headers).json()
    assert filtered == series[2:]


@pytest.mark.parametrize("value", [0, -1, "NaN", "Infinity"])
def test_reject_invalid_new_values(client, value):
    headers = auth(client)
    for field in ("weight_kg", "waist_cm"):
        result = client.post("/api/v1/measurements", headers=headers, json={"date": "2026-08-01", field: value})
        assert result.status_code == 422, result.text


def test_legacy_zero_retained_without_division_or_trend(client, db_session):
    headers = auth(client)
    row = post(client, headers, "2026-08-01", weight_kg=70, waist_cm=80)
    legacy = db_session.get(Measurement, row["id"])
    legacy.weight_kg = 0
    legacy.waist_cm = 0
    db_session.commit()
    post(client, headers, "2026-08-08", weight_kg=71, waist_cm=79)
    series = client.get("/api/v1/measurements/series", headers=headers).json()
    assert series[0]["weight_kg"] == 0
    assert series[0]["weight_ma"] is None
    assert series[1]["recomposition"] is None
    assert db_session.get(Measurement, row["id"]).weight_kg == 0


def test_notes_repeats_and_partial_update_preserve_originals(client):
    headers = auth(client)
    row = post(client, headers, "2026-08-01", weight_kg=70.123456789, waist_readings=[82.2, 82.4], notes="Same tape position")
    assert row["waist_cm"] == 82.3
    assert row["waist_readings"] == [82.2, 82.4]
    response = client.patch(f'/api/v1/measurements/{row["id"]}', headers=headers, json={"notes": "Changed note"})
    assert response.status_code == 200
    assert response.json()["weight_kg"] == row["weight_kg"]
    assert response.json()["waist_readings"] == row["waist_readings"]
    response = client.patch(f'/api/v1/measurements/{row["id"]}', headers=headers, json={"waist_readings": [81, 83, 85]})
    assert response.json()["waist_cm"] == 83
    response = client.patch(f'/api/v1/measurements/{row["id"]}', headers=headers, json={"waist_cm": 80})
    assert response.json()["waist_readings"] is None
    invalid = client.post("/api/v1/measurements", headers=headers, json={"date": "2026-08-02", "waist_readings": [81, 83], "waist_cm": 70})
    assert invalid.status_code == 422


def test_correct_date_without_overwriting_another_entry(client):
    headers = auth(client)
    first = post(client, headers, "2026-08-01", weight_kg=70)
    second = post(client, headers, "2026-08-02", waist_cm=80)
    url = f'/api/v1/measurements/{first["id"]}'
    assert client.patch(url, headers=headers, json={"date": "2026-08-02"}).status_code == 409
    assert client.patch(url, headers=headers, json={"date": None}).status_code == 422
    updated = client.patch(url, headers=headers, json={"date": "2026-08-03"})
    assert updated.status_code == 200
    assert updated.json()["id"] == first["id"]
    assert updated.json()["weight_kg"] == first["weight_kg"]
    rows = client.get("/api/v1/measurements", headers=headers).json()
    assert rows[0] == second


def test_delete_restore_preserves_id_values_and_ownership(client, db_session):
    headers = auth(client)
    other = auth(client, "other@example.com")
    row = post(client, headers, "2026-08-01", weight_kg=70, waist_readings=[81, 83], notes="Original")
    url = f'/api/v1/measurements/{row["id"]}'
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get("/api/v1/measurements", headers=headers).json() == []
    assert db_session.get(Measurement, row["id"]).deleted_at is not None
    assert client.get("/api/v1/measurements/deleted", headers=headers).json()[0]["id"] == row["id"]
    assert client.get("/api/v1/measurements/deleted", headers=other).json() == []
    assert client.post("/api/v1/measurements", headers=headers, json={"date": row["date"], "weight_kg": 99}).status_code == 409
    assert client.post(url + "/restore", headers=other).status_code == 404
    restored = client.post(url + "/restore", headers=headers)
    assert restored.status_code == 200
    for field in ("id", "date", "weight_kg", "waist_cm", "notes", "waist_readings", "created_at"):
        assert restored.json()[field] == row[field]
    assert client.post(url + "/restore", headers=headers).status_code == 409


def test_preferences_are_private_and_do_not_convert_stored_values(client):
    headers = auth(client)
    other = auth(client, "other@example.com")
    row = post(client, headers, "2026-08-01", weight_kg=70.123456789, waist_cm=82.3456789)
    response = client.patch("/api/v1/settings", headers=headers, json={"weight_unit": "lb", "waist_unit": "in", "weight_reminder_days": 1, "waist_reminder_days": 7})
    assert response.status_code == 200
    assert response.json()["weight_unit"] == "lb"
    assert client.get("/api/v1/settings", headers=other).json()["weight_unit"] == "kg"
    assert client.get("/api/v1/measurements", headers=headers).json() == [row]
    assert client.patch("/api/v1/settings", headers=headers, json={"weight_unit": "oz"}).status_code == 422
    assert client.patch("/api/v1/settings", headers=headers, json={"waist_reminder_days": -1}).status_code == 422


def test_csv_roundtrip_preview_and_keep_existing_by_default(client):
    headers = auth(client)
    original = post(client, headers, "2026-08-01", weight_kg=70.123456789, waist_readings=[81, 83], notes='Tape, level\n"repeat"')
    exported = client.get("/api/v1/measurements/export", headers=headers).json()["csv_text"]
    assert list(csv.DictReader(io.StringIO(exported)))[0]["notes"] == original["notes"]
    other = auth(client, "importer@example.com")
    preview = client.post("/api/v1/measurements/import", headers=other, json={"csv_text": exported})
    assert preview.status_code == 200, preview.text
    assert preview.json()["created"] == 1
    assert client.get("/api/v1/measurements", headers=other).json() == []
    result = client.post("/api/v1/measurements/import", headers=other, json={"csv_text": exported, "dry_run": False})
    assert result.status_code == 200, result.text
    imported = client.get("/api/v1/measurements", headers=other).json()[0]
    for field in ("date", "weight_kg", "waist_cm", "notes", "waist_readings"):
        assert imported[field] == original[field]
    result = client.post("/api/v1/measurements/import", headers=headers, json={"csv_text": "date,weight_kg\n2026-08-01,99\n", "dry_run": False})
    assert result.json()["skipped"] == 1
    assert client.get("/api/v1/measurements", headers=headers).json() == [original]


def test_csv_update_is_explicit_and_preserves_omitted_fields(client):
    headers = auth(client)
    row = post(client, headers, "2026-08-01", weight_kg=70, waist_cm=80, notes="Keep")
    result = client.post("/api/v1/measurements/import", headers=headers, json={"csv_text": "date,weight_lb\n2026-08-01,154\n", "conflict": "update", "dry_run": False})
    assert result.status_code == 200, result.text
    after = client.get("/api/v1/measurements", headers=headers).json()[0]
    assert after["weight_kg"] == pytest.approx(154 * 0.45359237)
    assert after["waist_cm"] == row["waist_cm"]
    assert after["notes"] == row["notes"]


@pytest.mark.parametrize("csv_text", [
    "date,weight_kg\n2026-08-01,75\n2026-08-02,0\n",
    "date,weight_kg\n2026-08-01,75\n2026-08-01,76\n",
    "date,weight_kg,weight_lb\n2026-08-01,75,165\n",
    "date,weight_kg\n2026-08-01,75,extra\n",
    "date,weight_kg\nnot-a-date,75\n",
    "date,weight_kg\n",
    "date,weight_kg\n2026-08-01,NaN\n",
    '"unterminated header',
])
def test_invalid_csv_is_atomic(client, csv_text):
    headers = auth(client)
    original = post(client, headers, "2026-07-01", weight_kg=70)
    response = client.post("/api/v1/measurements/import", headers=headers, json={"csv_text": csv_text, "dry_run": False})
    assert response.status_code == 422, response.text
    assert client.get("/api/v1/measurements", headers=headers).json() == [original]


def test_import_does_not_revive_deleted_entries(client):
    headers = auth(client)
    row = post(client, headers, "2026-08-01", weight_kg=70)
    client.delete(f'/api/v1/measurements/{row["id"]}', headers=headers)
    result = client.post("/api/v1/measurements/import", headers=headers, json={"csv_text": "date,weight_kg\n2026-08-01,75\n", "conflict": "update", "dry_run": False})
    assert result.json()["skipped"] == 1
    assert client.get("/api/v1/measurements", headers=headers).json() == []
