# app/db/models/workout_set.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sports_tracker.db.base import Base

from sports_tracker.db.models.session import Session
if TYPE_CHECKING:
    from sports_tracker.db.models.exercise import Exercise

class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    __table_args__ = (
        CheckConstraint(
            "set_type IN ('normal', 'warmup', 'drop', 'failure')",
            name="ck_workout_sets_set_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)

    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    set_type: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["Session"] = relationship(back_populates="workout_sets")
    exercise: Mapped["Exercise"] = relationship(back_populates="workout_sets")

    @property
    def exercise_name(self) -> str | None:
        return self.exercise.name if self.exercise else None
