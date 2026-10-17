# app/api/v1/endpoints/measurements.py
from __future__ import annotations

from collections import deque
from datetime import date, timedelta
from statistics import mean
import csv
import io

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sports_tracker.db.models.measurement import Measurement

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.repositories.measurement_repo import MeasurementRepository
from sports_tracker.db.repositories.user_settings_repo import UserSettingsRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.measurements import (
    MeasurementCreate,
    MeasurementImport,
    MeasurementRead,
    MeasurementUpdate,
    SeriesPointRead,
)

router = APIRouter()


@router.get("/measurements", response_model=list[MeasurementRead])
def list_measurements(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MeasurementRead]:
    rows = MeasurementRepository(db).list_for_user(
        current_user.id, start=start_date, end=end_date
    )
    return [MeasurementRead.model_validate(m) for m in rows]


@router.get("/measurements/series", response_model=list[SeriesPointRead])
def measurement_series(
    weight_window: int | None = Query(default=None, ge=1, le=365),
    waist_window: int | None = Query(default=None, ge=1, le=365),
    recomp_window: int | None = Query(default=None, ge=1, le=365),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SeriesPointRead]:
    settings = UserSettingsRepository(db).get_or_create(current_user.id)
    w_window = weight_window if weight_window is not None else settings.weight_ma_window
    a_window = waist_window if waist_window is not None else settings.waist_ma_window
    r_window = recomp_window if recomp_window is not None else settings.recomp_window

    # Warm up from history before filtering the response: a range request must
    # produce the same averages as the corresponding slice of the full history.
    rows = MeasurementRepository(db).list_for_user(current_user.id, end=end_date)
    wq: deque[tuple[date, float]] = deque()
    aq: deque[tuple[date, float]] = deque()
    w_hist: list[float] = []
    a_hist: list[float] = []
    points: list[SeriesPointRead] = []
    for m in rows:
        # Preserve the original index: each metric looks back N readings,
        # independently of the calendar-day windows used by moving averages.
        if m.weight_kg is not None:
            w_hist.append(m.weight_kg)
        if m.waist_cm is not None:
            a_hist.append(m.waist_cm)
        recomposition = None
        if (m.weight_kg is not None and m.weight_kg > 0
                and m.waist_cm is not None and m.waist_cm > 0
                and len(w_hist) > r_window and len(a_hist) > r_window):
            previous_weight = w_hist[-1 - r_window]
            previous_waist = a_hist[-1 - r_window]
            if previous_weight > 0 and previous_waist > 0:
                recomposition = round(
                    100 * (m.weight_kg / previous_weight - m.waist_cm / previous_waist), 2
                )
        for queue, window, value in ((wq, w_window, m.weight_kg), (aq, a_window, m.waist_cm)):
            cutoff = m.date - timedelta(days=window - 1)
            while queue and queue[0][0] < cutoff:
                queue.popleft()
            # Preserve legacy zero values in raw history, but don't use them in trends.
            if value is not None and value > 0:
                queue.append((m.date, value))
        if start_date is not None and m.date < start_date:
            continue
        points.append(SeriesPointRead(
            date=m.date,
            weight_kg=m.weight_kg,
            waist_cm=m.waist_cm,
            weight_ma=round(mean(v for _, v in wq), 2) if wq and m.weight_kg is not None and m.weight_kg > 0 else None,
            waist_ma=round(mean(v for _, v in aq), 2) if aq and m.waist_cm is not None and m.waist_cm > 0 else None,
            weight_count=len(wq),
            waist_count=len(aq),
            recomposition=recomposition,
        ))
    return points


@router.post("/measurements", response_model=MeasurementRead)
def upsert_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementRead:
    repo = MeasurementRepository(db)
    existing = repo.get_for_date(current_user.id, payload.date)
    if existing is not None and existing.deleted_at is not None:
        raise HTTPException(status_code=409, detail="A deleted entry exists on that date. Restore it from Deleted entries first.")
    measurement = repo.upsert(
        current_user.id,
        date_=payload.date,
        weight_kg=payload.weight_kg,
        waist_cm=payload.waist_cm,
        **payload.model_dump(include={"notes", "waist_readings"}, exclude_unset=True),
    )
    return MeasurementRead.model_validate(measurement)


@router.patch("/measurements/{measurement_id}", response_model=MeasurementRead)
def update_measurement(
    measurement_id: int,
    payload: MeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementRead:
    repo = MeasurementRepository(db)
    measurement = repo.get(measurement_id, current_user.id)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found"
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No fields to update",
        )

    if payload.waist_readings is not None:
        updates["waist_cm"] = payload.waist_cm
    elif "waist_cm" in updates:
        updates["waist_readings"] = None
    if "date" in updates and updates["date"] != measurement.date:
        existing = repo.get_for_date(current_user.id, updates["date"])
        if existing is not None:
            raise HTTPException(status_code=409, detail="That date already has an entry (possibly deleted). Restore or edit that entry instead.")
    new_weight = updates.get("weight_kg", measurement.weight_kg)
    new_waist = updates.get("waist_cm", measurement.waist_cm)
    if new_weight is None and new_waist is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one of weight_kg or waist_cm is required",
        )

    try:
        measurement = repo.update(measurement, **updates)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That date already has an entry")
    return MeasurementRead.model_validate(measurement)


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    repo = MeasurementRepository(db)
    measurement = repo.get(measurement_id, current_user.id)
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Measurement not found"
        )
    repo.delete(measurement)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/measurements/{measurement_id}/restore", response_model=MeasurementRead)
def restore_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementRead:
    measurement = db.scalar(select(Measurement).where(
        Measurement.id == measurement_id, Measurement.user_id == current_user.id,
    ))
    if measurement is None:
        raise HTTPException(status_code=404, detail="Measurement not found")
    if measurement.deleted_at is None:
        raise HTTPException(status_code=409, detail="Entry is already active; nothing was changed")
    return MeasurementRead.model_validate(MeasurementRepository(db).update(measurement, deleted_at=None))


@router.get("/measurements/export")
def export_measurements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["date", "weight_kg", "waist_cm", "notes", "waist_readings"])
    for row in MeasurementRepository(db).list_for_user(current_user.id):
        writer.writerow([row.date, row.weight_kg, row.waist_cm, row.notes,
                         "|".join(str(value) for value in row.waist_readings or [])])
    return {"csv_text": output.getvalue()}


@router.post("/measurements/import")
def import_measurements(
    payload: MeasurementImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    reader = csv.DictReader(io.StringIO(payload.csv_text.lstrip("\ufeff"), newline=""), strict=True)
    allowed = {"date", "weight_kg", "waist_cm", "weight_lb", "waist_in", "notes", "waist_readings"}
    try:
        fields = reader.fieldnames
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail=f"Invalid CSV header: {exc}")
    if not fields or "date" not in fields or set(fields) - allowed or len(set(fields)) != len(fields):
        raise HTTPException(status_code=422, detail="CSV needs a date column and supported columns: " + ", ".join(sorted(allowed)))
    repo = MeasurementRepository(db)
    planned = []
    seen = set()
    counts = {"created": 0, "updated": 0, "skipped": 0}
    try:
        for line, row in enumerate(reader, start=2):
            if line > 5001:
                raise ValueError("Maximum 5000 rows per import")
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Row {line}: column count does not match header")
            values = {"date": row["date"]}
            for metric, alternate, factor in (("weight_kg", "weight_lb", 0.45359237), ("waist_cm", "waist_in", 2.54)):
                if row.get(metric) and row.get(alternate):
                    raise ValueError(f"Row {line}: specify only one unit for each metric")
                if row.get(metric):
                    values[metric] = float(row[metric])
                elif row.get(alternate):
                    values[metric] = float(row[alternate]) * factor
            if "notes" in row:
                values["notes"] = row["notes"] or None
            if row.get("waist_readings"):
                values["waist_readings"] = [float(value) for value in row["waist_readings"].split("|")]
            entry = MeasurementCreate.model_validate(values)
            if entry.date in seen:
                raise ValueError(f"Row {line}: duplicate date {entry.date}")
            seen.add(entry.date)
            existing = repo.get_for_date(current_user.id, entry.date)
            action = "created" if existing is None else "updated"
            # Deleted entries are never revived by a bulk import.
            if existing is not None and (payload.conflict == "skip" or existing.deleted_at is not None):
                action = "skipped"
            counts[action] += 1
            planned.append((entry, existing, action))
    except (ValueError, ValidationError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail=f"Import rejected; no entries changed. {exc}")
    if not planned:
        raise HTTPException(status_code=422, detail="CSV has no measurement rows")
    if not payload.dry_run:
        for entry, existing, action in planned:
            if action == "skipped":
                continue
            changes = entry.model_dump(exclude_unset=True)
            if entry.waist_readings is not None:
                changes["waist_cm"] = entry.waist_cm
            elif "waist_cm" in changes:
                changes["waist_readings"] = None
            if existing is None:
                db.add(Measurement(user_id=current_user.id, **changes))
            else:
                for field, value in changes.items():
                    setattr(existing, field, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Dates changed during import. Preview again; no entries imported.")
    return {**counts, "dry_run": payload.dry_run,
            "preview": [{"date": str(entry.date), "action": action} for entry, _, action in planned[:20]]}


@router.get("/measurements/deleted", response_model=list[MeasurementRead])
def list_deleted_measurements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MeasurementRead]:
    rows = db.scalars(select(Measurement).where(
        Measurement.user_id == current_user.id, Measurement.deleted_at.is_not(None),
    ).order_by(Measurement.date.desc()))
    return [MeasurementRead.model_validate(row) for row in rows]
