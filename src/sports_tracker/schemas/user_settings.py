# app/schemas/user_settings.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserSettingsRead(BaseModel):
    weight_ma_window: int
    waist_ma_window: int
    recomp_window: int

    model_config = ConfigDict(from_attributes=True)


class UserSettingsUpdate(BaseModel):
    weight_ma_window: int | None = Field(default=None, ge=1, le=365)
    waist_ma_window: int | None = Field(default=None, ge=1, le=365)
    recomp_window: int | None = Field(default=None, ge=1, le=365)
