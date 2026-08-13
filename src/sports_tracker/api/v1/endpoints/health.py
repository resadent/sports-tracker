# app/api/v1/endpoints/health.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
import redis

from sports_tracker.db.session import get_db
from sports_tracker.health.checks import check_db, check_redis
from sports_tracker.settings import settings

router = APIRouter()


def get_redis() -> redis.Redis:
    # Redis client "simple": si falla ping, lo capturamos en el check.
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/health")
def health(
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    r = get_redis()

    db_res = check_db(db)
    redis_res = check_redis(r)

    overall_ok = db_res.ok and redis_res.ok

    if overall_ok:
        response.status_code = status.HTTP_200_OK
        return {"status": "ok", "db": "ok", "redis": "ok"}

    # Degradado: devolvemos 503 para que un load balancer/monitor lo vea
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "degraded",
        "db": "ok" if db_res.ok else "error",
        "redis": "ok" if redis_res.ok else "error",
        "details": {
            "db": db_res.detail,
            "redis": redis_res.detail,
        },
    }
