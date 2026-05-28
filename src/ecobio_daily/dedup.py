from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from ecobio_daily.models import SourceItem


_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,?#)\"']+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;"


def _normalize(doi: str) -> str:
    result = doi.lower()
    while result and result[-1] in _TRAILING_PUNCT:
        result = result[:-1]
    if result.startswith("10.17632/"):
        result = re.sub(r"\.\d+$", "", result)
    if result.startswith("10.6084/m9.figshare."):
        result = re.sub(r"\.v\d+$", "", result)
    return result


def extract_doi(item: SourceItem) -> str | None:
    for text in (item.url, item.id):
        if not text:
            continue
        match = _DOI_RE.search(text)
        if match:
            return _normalize(match.group(0))
    return None


def deduplicate_by_doi(items: list[SourceItem]) -> list[SourceItem]:
    seen_dois: set[str] = set()
    kept: list[SourceItem] = []
    for item in items:
        doi = extract_doi(item)
        if doi is None:
            kept.append(item)
            continue
        if doi in seen_dois:
            continue
        seen_dois.add(doi)
        kept.append(item)
    return kept


def filter_seen(
    items: list[SourceItem],
    seen: dict[str, str],
    today: date,
) -> list[SourceItem]:
    today_iso = today.isoformat()
    kept: list[SourceItem] = []
    for item in items:
        doi = extract_doi(item)
        if doi is None:
            kept.append(item)
            continue
        first_seen = seen.get(doi)
        if first_seen is None or first_seen >= today_iso:
            kept.append(item)
    return kept


def update_seen(
    seen: dict[str, str],
    items: list[SourceItem],
    today: date,
) -> None:
    today_iso = today.isoformat()
    for item in items:
        doi = extract_doi(item)
        if doi is None:
            continue
        if doi not in seen:
            seen[doi] = today_iso


def load_seen_dois(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def save_seen_dois(path: Path, seen: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(seen, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
