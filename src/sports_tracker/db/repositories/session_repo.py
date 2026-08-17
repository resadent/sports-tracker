# app/db/repositories/session_repo.py
from __future__ import annotations

from sqlalchemy import func, select, update
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

    def update_set(self, workout_set: WorkoutSet, **changes) -> WorkoutSet:
        for field, value in changes.items():
            if value is not None:
                setattr(workout_set, field, value)
        self.db.commit()
        self.db.refresh(workout_set)
        return workout_set

    def add_set(
        self,
        session: WorkoutSession,
        *,
        exercise_id: int,
        reps: int,
        weight: float,
        set_type: str = "normal",
        position: int | None = None,
    ) -> WorkoutSet:
        if position is None:
            position = self._next_position(session.id)
        else:
            self.db.execute(
                update(WorkoutSet)
                .where(
                    WorkoutSet.session_id == session.id,
                    WorkoutSet.position >= position,
                )
                .values(position=WorkoutSet.position + 1)
            )

        workout_set = WorkoutSet(
            session_id=session.id,
            exercise_id=exercise_id,
            reps=reps,
            weight=weight,
            set_type=set_type,
            position=position,
        )
        self.db.add(workout_set)
        self.db.commit()
        self.db.refresh(workout_set)
        return workout_set

    def reorder_sets(self, session_id: int, set_ids: list[int]) -> None:
        for index, set_id in enumerate(set_ids):
            self.db.execute(
                update(WorkoutSet)
                .where(
                    WorkoutSet.id == set_id,
                    WorkoutSet.session_id == session_id,
                )
                .values(position=index)
            )
        self.db.commit()

    def delete_set(self, workout_set: WorkoutSet) -> None:
        self.db.delete(workout_set)
        self.db.commit()

    def _next_position(self, session_id: int) -> int:
        max_position = self.db.scalar(
            select(func.max(WorkoutSet.position)).where(
                WorkoutSet.session_id == session_id
            )
        )
        return (max_position + 1) if max_position is not None else 0
