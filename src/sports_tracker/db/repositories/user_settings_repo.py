# app/db/repositories/user_settings_repo.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from sports_tracker.db.models.user_settings import UserSettings


class UserSettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user_id: int) -> UserSettings:
        settings = self.db.scalar(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        if settings is None:
            settings = UserSettings(
                user_id=user_id, weight_ma_window=7, waist_ma_window=7
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(
        self,
        user_id: int,
        weight_ma_window: int | None = None,
        waist_ma_window: int | None = None,
    ) -> UserSettings:
        settings = self.get_or_create(user_id)
        if weight_ma_window is not None:
            settings.weight_ma_window = weight_ma_window
        if waist_ma_window is not None:
            settings.waist_ma_window = waist_ma_window
        self.db.commit()
        self.db.refresh(settings)
        return settings
