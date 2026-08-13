# app/schemas/exercises.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MuscleRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=320)
    muscle_ids: list[int] = Field(default_factory=list)


class ExerciseRead(BaseModel):
    id: int
    name: str
    created_at: datetime
    muscles: list[MuscleRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
