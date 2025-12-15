# app/tasks/celery_app.py
from __future__ import annotations

from celery import Celery

from src.sports_tracker.settings import settings

celery_app = Celery(
    "training_metrics",
    broker=settings.settings.CELERY_BROKER_URL,
    backend=settings.settings.CELERY_RESULT_BACKEND,
)

# Config razonable
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Autodiscover de tasks (módulos dentro de app/tasks/)
celery_app.autodiscover_tasks(["app.tasks"])
