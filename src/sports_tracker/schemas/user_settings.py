# app/schemas/user_settings.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserSettingsRead(BaseModel):
    weight_ma_window: int
    waist_ma_window: int
    recomp_window: int

    weight_unit: Literal["kg", "lb"]
    waist_unit: Literal["cm", "in"]
    weight_reminder_days: int
    waist_reminder_days: int

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(BaseModel):
    weight_ma_window: int | None = Field(default=None, ge=1, le=365)
    waist_ma_window: int | None = Field(default=None, ge=1, le=365)
    recomp_window: int | None = Field(default=None, ge=1, le=365)

    weight_unit: Literal["kg", "lb"] | None = None
    waist_unit: Literal["cm", "in"] | None = None
    weight_reminder_days: int | None = Field(default=None, ge=0, le=365)
    waist_reminder_days: int | None = Field(default=None, ge=0, le=365)
