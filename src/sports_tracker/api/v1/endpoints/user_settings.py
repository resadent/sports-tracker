# app/api/v1/endpoints/user_settings.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sports_tracker.api.deps import get_current_user
from sports_tracker.db.models.user import User
from sports_tracker.db.repositories.user_settings_repo import UserSettingsRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.user_settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter()


@router.get("/settings", response_model=UserSettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsRead:
    settings = UserSettingsRepository(db).get_or_create(current_user.id)
    return UserSettingsRead.model_validate(settings)


@router.patch("/settings", response_model=UserSettingsRead)
def update_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsRead:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No fields to update",
        )
    settings = UserSettingsRepository(db).update(
        current_user.id,
        weight_ma_window=updates.get("weight_ma_window"),
        waist_ma_window=updates.get("waist_ma_window"),
    )
    return UserSettingsRead.model_validate(settings)
