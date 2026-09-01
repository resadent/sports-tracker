from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from sports_tracker.core.security import create_access_token, verify_password
from sports_tracker.db.repositories.user_repo import UserRepository
from sports_tracker.db.session import get_db
from sports_tracker.schemas.auth import Token
from sports_tracker.settings import settings

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db),
) -> Token:
    user = UserRepository(db).get_by_email(form_data.username)

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # "Remember me" logins get a long-lived token that survives browser restarts.
    expires_minutes = None
    if remember_me:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 24 * settings.REMEMBER_ME_EXPIRE_DAYS
    access_token = create_access_token(subject=str(user.id), expires_minutes=expires_minutes)
    return Token(access_token=access_token)
