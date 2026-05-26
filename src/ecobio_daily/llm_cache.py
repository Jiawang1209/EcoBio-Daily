from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def cache_key(
    model: str,
    messages: list[dict[str, Any]],
    response_format: str | None,
    temperature: float,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "response_format": response_format,
        "temperature": temperature,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def read_cache(cache_dir: Path, key: str) -> str | None:
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    value = data.get("value")
    return value if isinstance(value, str) else None


def write_cache(cache_dir: Path, key: str, value: str, model: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    record = {
        "value": value,
        "model": model,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
