# app/db/repositories/session_repo.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sports_tracker.db.models.session import Session as WorkoutSession
from sports_tracker.db.models.workout_set import WorkoutSet


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int) -> list[WorkoutSession]:
        return list(
            self.db.scalars(
                select(WorkoutSession)
                .options(
                    selectinload(WorkoutSession.workout_sets).selectinload(
                        WorkoutSet.exercise
                    )
                )
                .where(WorkoutSession.user_id == user_id)
                .order_by(WorkoutSession.created_at.desc())
            )
        )

    def get_for_user(self, session_id: int, user_id: int) -> WorkoutSession | None:
        return self.db.scalar(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.workout_sets).selectinload(
                    WorkoutSet.exercise
                )
            )
            .where(WorkoutSession.id == session_id, WorkoutSession.user_id == user_id)
        )

    def create(
        self,
        user_id: int,
        name: str | None,
        workout_sets: list[WorkoutSet],
    ) -> WorkoutSession:
        session = WorkoutSession(user_id=user_id, name=name, workout_sets=workout_sets)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def delete(self, session: WorkoutSession) -> None:
        self.db.delete(session)
        self.db.commit()

    def get_set(self, set_id: int, session_id: int) -> WorkoutSet | None:
        return self.db.scalar(
            select(WorkoutSet)
            .options(selectinload(WorkoutSet.exercise))
            .where(WorkoutSet.id == set_id, WorkoutSet.session_id == session_id)
        )

    def update_set(self, workout_set: WorkoutSet, reps: int | None, weight: float | None) -> WorkoutSet:
        if reps is not None:
            workout_set.reps = reps
        if weight is not None:
            workout_set.weight = weight
        self.db.commit()
        self.db.refresh(workout_set)
        return workout_set

    def delete_set(self, workout_set: WorkoutSet) -> None:
        self.db.delete(workout_set)
        self.db.commit()
