# app/schemas/measurements.py
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MeasurementCreate(BaseModel):
    date: date
    weight_kg: float | None = Field(default=None, ge=0)
    waist_cm: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _require_one_metric(self) -> "MeasurementCreate":
        if self.weight_kg is None and self.waist_cm is None:
            raise ValueError("At least one of weight_kg or waist_cm is required")
        return self


class MeasurementUpdate(BaseModel):
    weight_kg: float | None = Field(default=None, ge=0)
    waist_cm: float | None = Field(default=None, ge=0)


class MeasurementRead(BaseModel):
    id: int
    user_id: int
    date: date
    weight_kg: float | None
    waist_cm: float | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeriesPointRead(BaseModel):
    date: date
    weight_kg: float | None
    weight_ma: float | None
    waist_cm: float | None
    waist_ma: float | None
