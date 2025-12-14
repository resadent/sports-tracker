# app/health/checks.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

import redis


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    detail: Optional[str] = None


def check_db(db: Session) -> CheckResult:
    try:
        db.execute(text("SELECT 1"))
        return CheckResult(ok=True)
    except Exception as e:
        return CheckResult(ok=False, detail=f"{type(e).__name__}: {e}")


def check_redis(r: redis.Redis) -> CheckResult:
    try:
        r.ping()
        return CheckResult(ok=True)
    except Exception as e:
        return CheckResult(ok=False, detail=f"{type(e).__name__}: {e}")
