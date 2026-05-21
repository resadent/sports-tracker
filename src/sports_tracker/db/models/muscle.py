# app/db/models/muscle.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sports_tracker.db.base import Base
from sports_tracker.db.models.exercise import Exercise


class Muscle(Base):
    __tablename__ = "muscles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    exercises: Mapped[list["Exercise"]] = relationship(
        secondary="exercise_muscle", back_populates="muscles"
    )
