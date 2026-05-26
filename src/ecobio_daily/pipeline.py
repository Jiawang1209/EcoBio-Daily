from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.digest import build_digest
from ecobio_daily.fetch import fetch_source
from ecobio_daily.llm import LLMClient
from ecobio_daily.llm_digest import generate_section
from ecobio_daily.llm_scoring import batch_score
from ecobio_daily.models import Digest, ScoredItem, SourceItem
from ecobio_daily.render import render_digest
from ecobio_daily.scoring import deduplicate_items, score_item
from ecobio_daily.storage import write_json_records


LLM_SCORE_THRESHOLD = 6


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


def _attach_llm_briefs(digest: Digest, llm_client: LLMClient) -> None:
    ok = 0
    failed = 0
    for section in digest.sections:
        brief = generate_section(section.title, section.items, llm_client)
        section.llm_brief = brief
        if brief is None:
            failed += 1
        else:
            ok += 1
    print(f"LLM brief: {ok} ok, {failed} failed", file=sys.stderr)


def _apply_llm_scoring(
    scored_items: list[ScoredItem],
    llm_client: LLMClient,
    min_keyword_score: int,
    top_n: int,
) -> list[ScoredItem]:
    candidates = sorted(
        (s for s in scored_items if s.relevance_score >= min_keyword_score),
        key=lambda s: s.relevance_score,
        reverse=True,
    )[:top_n]
    if not candidates:
        return scored_items

    scores = batch_score([c.item for c in candidates], llm_client)
    for candidate, score in zip(candidates, scores):
        candidate.llm_score = score

    if all(s == -1 for s in scores):
        return scored_items

    return [c for c in candidates if c.llm_score is not None and c.llm_score >= LLM_SCORE_THRESHOLD]


def run_pipeline_from_items(
    items: list[SourceItem],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
    llm_client: LLMClient | None = None,
    llm_max_items: int = 12,
) -> Path:
    write_json_records(_raw_items_path(output_root, digest_date), items)
    windowed_items = _filter_items_by_date_window(
        items,
        digest_date=digest_date,
        lookback_days=digest_config.lookback_days,
    )
    unique_items = deduplicate_items(windowed_items)
    scored_items = [score_item(item, topics) for item in unique_items]
    if llm_client is not None:
        scored_items = _apply_llm_scoring(
            scored_items,
            llm_client=llm_client,
            min_keyword_score=digest_config.min_relevance_score,
            top_n=llm_max_items,
        )
    write_json_records(_scored_items_path(output_root, digest_date), scored_items)
    digest = build_digest(
        digest_date=digest_date,
        title=digest_config.title,
        scored_items=scored_items,
        min_relevance_score=digest_config.min_relevance_score,
        max_items=digest_config.max_items,
        highlight_count=digest_config.highlights,
    )
    if llm_client is not None:
        _attach_llm_briefs(digest, llm_client)
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
    llm_client: LLMClient | None = None,
    llm_max_items: int = 12,
) -> Path:
    items: list[SourceItem] = []
    for source in sources:
        try:
            items.extend(fetch_source(source))
        except Exception as error:
            print(f"Skipping source {source.id}: {error}", file=sys.stderr)
    return run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=digest_config,
        digest_date=digest_date,
        template_path=template_path,
        output_root=output_root,
        llm_client=llm_client,
        llm_max_items=llm_max_items,
    )
