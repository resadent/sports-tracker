# app/schemas/sessions.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkoutSetCreate(BaseModel):
    exercise_id: int
    reps: int = Field(gt=0)
    weight: float = Field(default=0.0, ge=0)


class WorkoutSetUpdate(BaseModel):
    reps: int | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, ge=0)


class WorkoutSetRead(BaseModel):
    id: int
    session_id: int
    exercise_id: int
    exercise_name: str | None = None
    reps: int
    weight: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    name: str | None = Field(default=None, max_length=320)
    workout_sets: list[WorkoutSetCreate] = Field(default_factory=list)


class SessionRead(BaseModel):
    id: int
    user_id: int
    name: str | None
    created_at: datetime
    workout_sets: list[WorkoutSetRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
