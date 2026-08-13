"""Idempotently seed a small catalog of exercises and the muscles they train.

Run with: python -m sports_tracker.db.seed_data
"""
from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from sports_tracker.settings import settings
from sports_tracker.db.models.muscle import Muscle
from sports_tracker.db.models.exercise import Exercise

# exercise name -> muscles it trains
EXERCISES: dict[str, list[str]] = {
    "Quadriceps Extension": ["Quadriceps"],
    "Barbell Squat": ["Quadriceps", "Hamstrings", "Glutes"],
    "Bench Press": ["Chest", "Triceps", "Shoulders"],
    "Pull-Up": ["Back", "Biceps"],
}


def seed_database() -> None:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        # Get or create every muscle first, so exercises can reference them.
        muscles: dict[str, Muscle] = {}
        for muscle_name in {m for names in EXERCISES.values() for m in names}:
            muscle = db.scalar(select(Muscle).where(Muscle.name == muscle_name))
            if muscle is None:
                muscle = Muscle(name=muscle_name)
                db.add(muscle)
            muscles[muscle_name] = muscle
        db.flush()

        for exercise_name, muscle_names in EXERCISES.items():
            exercise = db.scalar(select(Exercise).where(Exercise.name == exercise_name))
            if exercise is None:
                exercise = Exercise(
                    name=exercise_name,
                    muscles=[muscles[name] for name in muscle_names],
                )
                db.add(exercise)

        db.commit()


if __name__ == "__main__":
    seed_database()
