# app/api/v1/endpoints/measurements.py
from __future__ import annotations

from collections import deque
from datetime import date
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.repositories.measurement_repo import MeasurementRepository
from sports_tracker.db.repositories.user_settings_repo import UserSettingsRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.measurements import (
    MeasurementCreate,
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

    rows = MeasurementRepository(db).list_for_user(
        current_user.id, start=start_date, end=end_date
    )

    wq: deque[float] = deque(maxlen=w_window)
    aq: deque[float] = deque(maxlen=a_window)
    w_hist: list[float] = []
    a_hist: list[float] = []
    points: list[SeriesPointRead] = []
    for m in rows:
        if m.weight_kg is not None:
            wq.append(m.weight_kg)
            w_hist.append(m.weight_kg)
        if m.waist_cm is not None:
            aq.append(m.waist_cm)
            a_hist.append(m.waist_cm)

        recomposition = None
        if m.weight_kg is not None and m.waist_cm is not None:
            wi = len(w_hist) - 1
            ai = len(a_hist) - 1
            # Compare to the value r_window readings back for each metric.
            if wi >= r_window and ai >= r_window:
                recomposition = round(
                    100
                    * (m.weight_kg / w_hist[wi - r_window] - m.waist_cm / a_hist[ai - r_window]),
                    2,
                )

        points.append(
            SeriesPointRead(
                date=m.date,
                weight_kg=m.weight_kg,
                weight_ma=round(mean(wq), 2) if wq else None,
                waist_cm=m.waist_cm,
                waist_ma=round(mean(aq), 2) if aq else None,
                recomposition=recomposition,
            )
        )
    return points


@router.post("/measurements", response_model=MeasurementRead)
def upsert_measurement(
    payload: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeasurementRead:
    measurement = MeasurementRepository(db).upsert(
        current_user.id,
        date_=payload.date,
        weight_kg=payload.weight_kg,
        waist_cm=payload.waist_cm,
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

    new_weight = updates.get("weight_kg", measurement.weight_kg)
    new_waist = updates.get("waist_cm", measurement.waist_cm)
    if new_weight is None and new_waist is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one of weight_kg or waist_cm is required",
        )

    measurement = repo.update(measurement, **updates)
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
