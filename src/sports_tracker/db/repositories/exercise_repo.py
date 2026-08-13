# app/db/repositories/exercise_repo.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sports_tracker.db.models.exercise import Exercise
from sports_tracker.db.models.muscle import Muscle


class ExerciseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Exercise]:
        return list(
            self.db.scalars(
                select(Exercise)
                .options(selectinload(Exercise.muscles))
                .order_by(Exercise.name)
            )
        )

    def get_by_id(self, exercise_id: int) -> Exercise | None:
        return self.db.scalar(
            select(Exercise)
            .options(selectinload(Exercise.muscles))
            .where(Exercise.id == exercise_id)
        )

    def get_by_name(self, name: str) -> Exercise | None:
        return self.db.scalar(select(Exercise).where(Exercise.name == name))

    def create(self, name: str, muscles: list[Muscle]) -> Exercise:
        exercise = Exercise(name=name, muscles=muscles)
        self.db.add(exercise)
        self.db.commit()
        self.db.refresh(exercise)
        return exercise


class MuscleRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Muscle]:
        return list(self.db.scalars(select(Muscle).order_by(Muscle.name)))

    def get_by_id(self, muscle_id: int) -> Muscle | None:
        return self.db.get(Muscle, muscle_id)
