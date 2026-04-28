from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from ecobio_daily.config import SourceConfig
from ecobio_daily.models import SourceItem


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _entry_datetime(entry: dict) -> datetime:
    value = (
        entry.get("published")
        or entry.get("updated")
        or entry.get("prism_publicationdate")
    )
    return _parse_datetime(value)


def parse_rss(xml: str, source_id: str, source_name: str) -> list[SourceItem]:
    feed = feedparser.parse(xml)
    items: list[SourceItem] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        item_id = entry.get("id") or entry.get("guid") or url
        item = SourceItem(
            id=str(item_id),
            title=entry.get("title", "").strip(),
            url=url,
            source=source_name,
            published_at=_entry_datetime(entry),
            summary=entry.get("summary", ""),
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def fetch_source(source: SourceConfig, timeout_seconds: float = 20.0) -> list[SourceItem]:
    if source.type != "rss":
        raise ValueError(f"Unsupported source type: {source.type}")
    response = httpx.get(str(source.url), timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    return parse_rss(response.text, source_id=source.id, source_name=source.name)
