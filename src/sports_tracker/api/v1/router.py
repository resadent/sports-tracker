# app/api/v1/router.py
from __future__ import annotations

from fastapi import APIRouter

# Endpoints (los crearás luego; estos imports deben existir cuando los añadas)
from sports_tracker.api.v1.endpoints.health import router as health_router
from sports_tracker.api.v1.endpoints.users import router as users_router
# from app.api.v1.endpoints.auth import router as auth_router
# from app.api.v1.endpoints.training_sessions import router as training_router
# from app.api.v1.endpoints.body_metrics import router as body_metrics_router
# from app.api.v1.endpoints.metrics import router as metrics_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(users_router, tags=["users"])

# Cuando crees los routers, descomenta:
# api_v1_router.include_router(health_router, tags=["health"])
# api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
# api_v1_router.include_router(training_router, prefix="/training-sessions", tags=["training"])
# api_v1_router.include_router(body_metrics_router, prefix="/body-metrics", tags=["body-metrics"])
# api_v1_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
