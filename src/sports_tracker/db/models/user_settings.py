# app/db/models/user_settings.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sports_tracker.db.base import Base

if TYPE_CHECKING:
    from sports_tracker.db.models.user import User


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    weight_ma_window: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")
    waist_ma_window: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")
    recomp_window: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship()
