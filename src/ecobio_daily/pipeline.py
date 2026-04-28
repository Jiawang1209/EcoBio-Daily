from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.digest import build_digest
from ecobio_daily.fetch import fetch_source
from ecobio_daily.models import SourceItem
from ecobio_daily.render import render_digest
from ecobio_daily.scoring import deduplicate_items, score_item
from ecobio_daily.storage import write_json_records


def _output_path(output_root: Path, pattern: str, digest_date: date) -> Path:
    relative = pattern.format(
        year=f"{digest_date.year:04d}",
        month=f"{digest_date.month:02d}",
        date=digest_date.isoformat(),
    )
    return output_root / relative


def _filter_items_by_date_window(
    items: list[SourceItem],
    digest_date: date,
    lookback_days: int,
) -> list[SourceItem]:
    start_date = digest_date - timedelta(days=lookback_days)
    return [
        item
        for item in items
        if start_date <= item.published_date <= digest_date
    ]


def _raw_items_path(output_root: Path, digest_date: date) -> Path:
    return output_root / "data" / "raw" / f"{digest_date.isoformat()}-items.json"


def _scored_items_path(output_root: Path, digest_date: date) -> Path:
    return output_root / "data" / "processed" / f"{digest_date.isoformat()}-scored.json"


def run_pipeline_from_items(
    items: list[SourceItem],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
) -> Path:
    write_json_records(_raw_items_path(output_root, digest_date), items)
    windowed_items = _filter_items_by_date_window(
        items,
        digest_date=digest_date,
        lookback_days=digest_config.lookback_days,
    )
    unique_items = deduplicate_items(windowed_items)
    scored_items = [score_item(item, topics) for item in unique_items]
    write_json_records(_scored_items_path(output_root, digest_date), scored_items)
    digest = build_digest(
        digest_date=digest_date,
        title=digest_config.title,
        scored_items=scored_items,
        min_relevance_score=digest_config.min_relevance_score,
        max_items=digest_config.max_items,
        highlight_count=digest_config.highlights,
    )
    markdown = render_digest(digest, template_path)
    output_path = _output_path(output_root, digest_config.output_pattern, digest_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def run_pipeline(
    sources: list[SourceConfig],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
) -> Path:
    items: list[SourceItem] = []
    for source in sources:
        items.extend(fetch_source(source))
    return run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=digest_config,
        digest_date=digest_date,
        template_path=template_path,
        output_root=output_root,
    )
