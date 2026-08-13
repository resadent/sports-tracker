# app/api/v1/endpoints/users.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sports_tracker.core.security import hash_password
from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.session import get_db
from sports_tracker.db.repositories.user_repo import UserRepository
from sports_tracker.schemas.users import UserCreate, UserRead

router = APIRouter()


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    repo = UserRepository(db)

    if repo.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = repo.create(email=payload.email, hashed_password=hash_password(payload.password))
    return UserRead.model_validate(user)


@router.get(
    "/users/me",
    response_model=UserRead,
)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/users/{user_id}",
    response_model=UserRead,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserRead.model_validate(user)
