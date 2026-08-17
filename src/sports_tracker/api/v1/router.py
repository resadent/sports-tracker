# app/api/v1/router.py
from __future__ import annotations

from fastapi import APIRouter

# Endpoints (los crearás luego; estos imports deben existir cuando los añadas)
from sports_tracker.api.v1.endpoints.health import router as health_router
from sports_tracker.api.v1.endpoints.users import router as users_router
from sports_tracker.api.v1.endpoints.auth import router as auth_router
from sports_tracker.api.v1.endpoints.exercises import router as exercises_router
from sports_tracker.api.v1.endpoints.sessions import router as sessions_router
from sports_tracker.api.v1.endpoints.measurements import router as measurements_router
from sports_tracker.api.v1.endpoints.user_settings import router as user_settings_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(users_router, tags=["users"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(exercises_router, tags=["exercises"])
api_v1_router.include_router(sessions_router, tags=["sessions"])
api_v1_router.include_router(measurements_router, tags=["measurements"])
api_v1_router.include_router(user_settings_router, tags=["settings"])
