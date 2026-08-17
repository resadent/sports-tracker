# app/api/v1/endpoints/sessions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.models.workout_set import WorkoutSet
from sports_tracker.db.repositories.exercise_repo import ExerciseRepository
from sports_tracker.db.repositories.session_repo import SessionRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.sessions import (
    SessionCreate,
    SessionRead,
    WorkoutSetCreate,
    WorkoutSetOrderUpdate,
    WorkoutSetRead,
    WorkoutSetUpdate,
)

router = APIRouter()


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return SessionRepository(db).list_for_user(current_user.id)


@router.post(
    "/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionRead:
    exercise_repo = ExerciseRepository(db)
    workout_sets = []
    for index, set_payload in enumerate(payload.workout_sets):
        if exercise_repo.get_by_id(set_payload.exercise_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise {set_payload.exercise_id} not found",
            )
        position = set_payload.position if set_payload.position is not None else index
        workout_sets.append(
            WorkoutSet(
                exercise_id=set_payload.exercise_id,
                reps=set_payload.reps,
                weight=set_payload.weight,
                set_type=set_payload.set_type.value,
                position=position,
            )
        )

    session = SessionRepository(db).create(
        user_id=current_user.id,
        name=payload.name,
        workout_sets=workout_sets,
    )
    return SessionRead.model_validate(session)


@router.get("/sessions/{session_id}", response_model=SessionRead)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionRead:
    session = _get_owned_session(session_id, current_user.id, db)
    return SessionRead.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_owned_session(session_id, current_user.id, db)
    SessionRepository(db).delete(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/workout-sets",
    response_model=WorkoutSetRead,
    status_code=status.HTTP_201_CREATED,
)
def add_workout_set(
    session_id: int,
    payload: WorkoutSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSetRead:
    session = _get_owned_session(session_id, current_user.id, db)
    if ExerciseRepository(db).get_by_id(payload.exercise_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise {payload.exercise_id} not found",
        )
    workout_set = SessionRepository(db).add_set(
        session,
        exercise_id=payload.exercise_id,
        reps=payload.reps,
        weight=payload.weight,
        set_type=payload.set_type.value,
        position=payload.position,
    )
    return WorkoutSetRead.model_validate(workout_set)


@router.put(
    "/sessions/{session_id}/workout-sets/order",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reorder_workout_sets(
    session_id: int,
    payload: WorkoutSetOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    session = _get_owned_session(session_id, current_user.id, db)
    existing_ids = {ws.id for ws in session.workout_sets}
    if len(payload.set_ids) != len(existing_ids) or set(payload.set_ids) != existing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="set_ids must be a permutation of the session's workout sets",
        )
    SessionRepository(db).reorder_sets(session_id, payload.set_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/sessions/{session_id}/workout-sets/{set_id}",
    response_model=WorkoutSetRead,
)
def update_workout_set(
    session_id: int,
    set_id: int,
    payload: WorkoutSetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSetRead:
    _get_owned_session(session_id, current_user.id, db)
    repo = SessionRepository(db)
    workout_set = repo.get_set(set_id, session_id)
    if workout_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout set not found",
        )
    changes = payload.model_dump(exclude_unset=True, mode="json")
    updated = repo.update_set(workout_set, **changes)
    return WorkoutSetRead.model_validate(updated)


@router.delete(
    "/sessions/{session_id}/workout-sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workout_set(
    session_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    _get_owned_session(session_id, current_user.id, db)
    repo = SessionRepository(db)
    workout_set = repo.get_set(set_id, session_id)
    if workout_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout set not found",
        )
    repo.delete_set(workout_set)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_owned_session(session_id: int, user_id: int, db: Session):
    session = SessionRepository(db).get_for_user(session_id, user_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session
