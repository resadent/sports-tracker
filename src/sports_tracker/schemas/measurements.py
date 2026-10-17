from __future__ import annotations

from datetime import date as Date, datetime
from statistics import mean
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveMeasurement = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class MeasurementContext(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    waist_readings: list[PositiveMeasurement] | None = Field(default=None, min_length=2, max_length=5)

    @model_validator(mode="after")
    def average_repeats(self):
        if self.waist_readings is not None:
            average = round(mean(self.waist_readings), 2)
            if self.waist_cm is not None and abs(self.waist_cm - average) > 0.051:
                raise ValueError("Waist must match the average of repeat readings")
            self.waist_cm = average
        return self


class MeasurementCreate(MeasurementContext):
    date: Date
    weight_kg: PositiveMeasurement | None = None
    waist_cm: PositiveMeasurement | None = None

    @model_validator(mode="after")
    def _require_one_metric(self):
        if self.weight_kg is None and self.waist_cm is None:
            raise ValueError("At least one of weight_kg or waist_cm is required")
        return self


class MeasurementUpdate(MeasurementContext):
    date: Date | None = None
    weight_kg: PositiveMeasurement | None = None
    waist_cm: PositiveMeasurement | None = None

    @model_validator(mode="after")
    def valid_date(self):
        if "date" in self.model_fields_set and self.date is None:
            raise ValueError("Date cannot be empty")
        return self


class MeasurementRead(BaseModel):
    id: int
    user_id: int
    date: Date
    weight_kg: float | None
    waist_cm: float | None
    notes: str | None = None
    waist_readings: list[float] | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SeriesPointRead(BaseModel):
    date: Date
    weight_kg: float | None
    weight_ma: float | None
    waist_cm: float | None
    waist_ma: float | None
    weight_count: int = 0
    waist_count: int = 0
    # Original percentage-change index, using the saved reading lookback.
    recomposition: float | None = None


class MeasurementImport(BaseModel):
    csv_text: str = Field(max_length=1_000_000)
    conflict: Literal["skip", "update"] = "skip"
    dry_run: bool = True
