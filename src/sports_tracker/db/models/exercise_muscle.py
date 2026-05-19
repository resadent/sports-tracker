# app/db/models/exercise_muscle.py
from sqlalchemy import Column, ForeignKey, Integer, Table

from sports_tracker.db.base import Base

exercise_muscle = Table(
    "exercise_muscle",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("muscle_id", Integer, ForeignKey("muscles.id", ondelete="CASCADE"), primary_key=True),
)