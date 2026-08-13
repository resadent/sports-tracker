# app/api/v1/endpoints/exercises.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.repositories.exercise_repo import ExerciseRepository, MuscleRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.exercises import ExerciseCreate, ExerciseRead, MuscleRead

router = APIRouter()


@router.get("/exercises", response_model=list[ExerciseRead])
def list_exercises(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return ExerciseRepository(db).list()


@router.post(
    "/exercises",
    response_model=ExerciseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    payload: ExerciseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ExerciseRead:
    repo = ExerciseRepository(db)

    if repo.get_by_name(payload.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exercise with this name already exists",
        )

    muscle_repo = MuscleRepository(db)
    muscles = []
    for muscle_id in payload.muscle_ids:
        muscle = muscle_repo.get_by_id(muscle_id)
        if muscle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Muscle {muscle_id} not found",
            )
        muscles.append(muscle)

    exercise = repo.create(name=payload.name, muscles=muscles)
    return ExerciseRead.model_validate(exercise)


@router.get("/exercises/{exercise_id}", response_model=ExerciseRead)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ExerciseRead:
    exercise = ExerciseRepository(db).get_by_id(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )
    return ExerciseRead.model_validate(exercise)


@router.get("/muscles", response_model=list[MuscleRead])
def list_muscles(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return MuscleRepository(db).list()
