from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


class RunMetrics:
    def __init__(self, digest_date: date):
        self.digest_date = digest_date
        self.started_at = datetime.now(timezone.utc)
        self._started_perf = time.perf_counter()
        self.completed_at: datetime | None = None
        self.duration_seconds: float = 0.0
        self.stages: dict[str, Any] = {}

    def record(self, stage: str, **kwargs: Any) -> None:
        self.stages[stage] = dict(kwargs)

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.duration_seconds = time.perf_counter() - self._started_perf

    def save(self, path: Path) -> None:
        if self.completed_at is None:
            self.finalize()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "date": self.digest_date.isoformat(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 3),
            "stages": self.stages,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
