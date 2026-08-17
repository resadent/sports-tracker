# app/db/repositories/measurement_repo.py
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from sports_tracker.db.models.measurement import Measurement


class MeasurementRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_date(self, user_id: int, date_: date) -> Measurement | None:
        return self.db.scalar(
            select(Measurement).where(
                Measurement.user_id == user_id, Measurement.date == date_
            )
        )

    def get(self, measurement_id: int, user_id: int) -> Measurement | None:
        return self.db.scalar(
            select(Measurement).where(
                Measurement.id == measurement_id, Measurement.user_id == user_id
            )
        )

    def upsert(
        self,
        user_id: int,
        date_: date,
        weight_kg: float | None = None,
        waist_cm: float | None = None,
    ) -> Measurement:
        measurement = self.get_for_date(user_id, date_)
        if measurement is None:
            measurement = Measurement(
                user_id=user_id,
                date=date_,
                weight_kg=weight_kg,
                waist_cm=waist_cm,
            )
            self.db.add(measurement)
        else:
            if weight_kg is not None:
                measurement.weight_kg = weight_kg
            if waist_cm is not None:
                measurement.waist_cm = waist_cm
        self.db.commit()
        self.db.refresh(measurement)
        return measurement

    def update(self, measurement: Measurement, **changes) -> Measurement:
        for field, value in changes.items():
            setattr(measurement, field, value)
        self.db.commit()
        self.db.refresh(measurement)
        return measurement

    def delete(self, measurement: Measurement) -> None:
        self.db.delete(measurement)
        self.db.commit()

    def list_for_user(
        self, user_id: int, start: date | None = None, end: date | None = None
    ) -> list[Measurement]:
        stmt = select(Measurement).where(Measurement.user_id == user_id)
        if start is not None:
            stmt = stmt.where(Measurement.date >= start)
        if end is not None:
            stmt = stmt.where(Measurement.date <= end)
        stmt = stmt.order_by(Measurement.date)
        return list(self.db.scalars(stmt))
