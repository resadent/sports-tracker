# app/db/models/exercise_muscle.py
from sqlalchemy import Column, ForeignKey, Integer, Table, Boolean

from sports_tracker.db.base import Base

exercise_muscle = Table(
    "exercise_muscle",
    Base.metadata,
    Column("exercise_id", ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("muscle_id", ForeignKey("muscles.id", ondelete="CASCADE"), primary_key=True),
    Column("lengthened_partial", Boolean, default=0)
)