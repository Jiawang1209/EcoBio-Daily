from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any
import sys

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.dedup import (
    deduplicate_by_doi,
    filter_seen,
    load_seen_dois,
    save_seen_dois,
    update_seen,
)
from ecobio_daily.digest import build_digest
from ecobio_daily.fetch import fetch_source
from ecobio_daily.llm import LLMClient
from ecobio_daily.llm_digest import generate_section
from ecobio_daily.llm_grounding import check_groundedness
from ecobio_daily.llm_scoring import batch_score
from ecobio_daily.models import Digest, ScoredItem, SourceItem
from ecobio_daily.render import render_digest
from ecobio_daily.run_metrics import RunMetrics
from ecobio_daily.scoring import deduplicate_items, score_item
from ecobio_daily.storage import write_json_records


LLM_SCORE_THRESHOLD = 6
LLM_BACKFILL_SCORE_THRESHOLD = 4


def _output_path(
    output_root: Path,
    pattern: str,
    digest_date: date,
    lang: str = "zh",
) -> Path:
    relative = pattern.format(
        year=f"{digest_date.year:04d}",
        month=f"{digest_date.month:02d}",
        date=digest_date.isoformat(),
        lang=lang,
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


def _seen_dois_path(output_root: Path) -> Path:
    return output_root / "data" / "state" / "seen_dois.json"


def _attach_llm_briefs(
    digest: Digest,
    llm_client: LLMClient,
    metrics: RunMetrics | None = None,
) -> None:
    ok = 0
    failed = 0
    grounded = 0
    ungrounded = 0
    errored = 0
    repaired = 0
    for section in digest.sections:
        brief = generate_section(section.title, section.items, llm_client)
        section.llm_brief = brief
        if brief is None:
            failed += 1
            continue
        ok += 1
        brief_items = brief.get("items") or []
        for i, scored in enumerate(section.items):
            if i < len(brief_items) and isinstance(brief_items[i], dict):
                scored.llm_brief_item = brief_items[i]
                verdict = check_groundedness(
                    scored.item.summary, brief_items[i], llm_client
                )
                scored.llm_grounding = verdict
                if verdict is None:
                    errored += 1
                    scored.llm_brief_item = None
                    repaired += 1
                    continue
                if verdict.get("grounded") and int(verdict.get("score", 0)) >= 7:
                    grounded += 1
                else:
                    scored.llm_brief_item = None
                    repaired += 1
    print(f"LLM brief: {ok} ok, {failed} failed", file=sys.stderr)
    print(
        f"LLM grounding: {grounded} passed, {ungrounded} failed, {repaired} repaired",
        file=sys.stderr,
    )
    if metrics is not None:
        metrics.record("llm_brief", ok=ok, failed=failed)
        metrics.record(
            "llm_grounding",
            passed=grounded,
            failed=ungrounded,
            errored=errored,
            repaired=repaired,
        )


def _apply_llm_scoring(
    scored_items: list[ScoredItem],
    llm_client: LLMClient,
    min_keyword_score: int,
    top_n: int,
    target_min_items: int,
    metrics: RunMetrics | None = None,
) -> list[ScoredItem]:
    candidates = sorted(
        (
            s
            for s in scored_items
            if s.relevance_score >= min_keyword_score and s.item.summary.strip()
        ),
        key=lambda s: s.relevance_score,
        reverse=True,
    )[:top_n]
    if not candidates:
        if metrics is not None:
            metrics.record(
                "llm_relevance", candidates=0, kept=0, fallback_used=False
            )
        return scored_items

    scores = batch_score([c.item for c in candidates], llm_client)
    for candidate, score in zip(candidates, scores):
        candidate.llm_score = score

    if all(s == -1 for s in scores):
        if metrics is not None:
            metrics.record(
                "llm_relevance",
                candidates=len(candidates),
                kept=len(candidates),
                fallback_used=True,
            )
        return scored_items

    kept = [
        c for c in candidates if c.llm_score is not None and c.llm_score >= LLM_SCORE_THRESHOLD
    ]
    backfilled = 0
    if len(kept) < target_min_items:
        kept_ids = {id(item) for item in kept}
        backfill_candidates = [
            c
            for c in sorted(candidates, key=lambda item: item.llm_score or -1, reverse=True)
            if id(c) not in kept_ids
            and c.llm_score is not None
            and c.llm_score >= LLM_BACKFILL_SCORE_THRESHOLD
        ]
        needed = target_min_items - len(kept)
        kept.extend(backfill_candidates[:needed])
        backfilled = min(needed, len(backfill_candidates))
    if metrics is not None:
        metrics.record(
            "llm_relevance",
            candidates=len(candidates),
            kept=len(kept),
            backfilled=backfilled,
            fallback_used=False,
        )
    return kept


def run_pipeline_from_items(
    items: list[SourceItem],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
    llm_client: LLMClient | None = None,
    llm_max_items: int = 12,
    metrics: RunMetrics | None = None,
) -> Path:
    write_json_records(_raw_items_path(output_root, digest_date), items)
    windowed_items = _filter_items_by_date_window(
        items,
        digest_date=digest_date,
        lookback_days=digest_config.lookback_days,
    )
    if metrics is not None:
        metrics.record("date_window", in_count=len(items), out_count=len(windowed_items))

    unique_items = deduplicate_items(windowed_items)
    if metrics is not None:
        metrics.record(
            "url_dedup", in_count=len(windowed_items), out_count=len(unique_items)
        )

    after_intra_doi = deduplicate_by_doi(unique_items)
    if metrics is not None:
        metrics.record(
            "intra_day_doi_dedup",
            in_count=len(unique_items),
            out_count=len(after_intra_doi),
        )
    unique_items = after_intra_doi

    seen_path = _seen_dois_path(output_root)
    seen = load_seen_dois(seen_path)
    after_cross_day = filter_seen(unique_items, seen, today=digest_date)
    if metrics is not None:
        metrics.record(
            "cross_day_doi_dedup",
            in_count=len(unique_items),
            out_count=len(after_cross_day),
            prior_seen_count=len(seen),
        )
    unique_items = after_cross_day

    scored_items = [score_item(item, topics) for item in unique_items]
    if metrics is not None:
        above_threshold = sum(
            1 for s in scored_items if s.relevance_score >= digest_config.min_relevance_score
        )
        metrics.record(
            "keyword_score",
            in_count=len(scored_items),
            above_threshold=above_threshold,
        )
    if llm_client is not None:
        scored_items = _apply_llm_scoring(
            scored_items,
            llm_client=llm_client,
            min_keyword_score=digest_config.min_relevance_score,
            top_n=llm_max_items,
            target_min_items=digest_config.target_items_min,
            metrics=metrics,
        )
    digest = build_digest(
        digest_date=digest_date,
        title=digest_config.title,
        scored_items=scored_items,
        min_relevance_score=digest_config.min_relevance_score,
        max_items=digest_config.max_items,
        highlight_count=digest_config.highlights,
    )
    if metrics is not None:
        metrics.record(
            "build_digest",
            sections=len(digest.sections),
            items=sum(len(s.items) for s in digest.sections),
            highlights=len(digest.highlights),
        )
    if llm_client is not None:
        _attach_llm_briefs(digest, llm_client, metrics=metrics)
    write_json_records(_scored_items_path(output_root, digest_date), scored_items)
    markdown_zh = render_digest(digest, template_path)
    zh_path = _output_path(
        output_root, digest_config.output_pattern, digest_date, lang="zh"
    )
    zh_path.parent.mkdir(parents=True, exist_ok=True)
    zh_path.write_text(markdown_zh, encoding="utf-8")

    if llm_client is not None:
        en_template_path = template_path.with_name(
            template_path.name.replace("_zh.", "_en.")
        )
        markdown_en = render_digest(digest, en_template_path)
        en_path = _output_path(
            output_root, digest_config.output_pattern, digest_date, lang="en"
        )
        en_path.write_text(markdown_en, encoding="utf-8")

    update_seen(seen, digest.references, today=digest_date)
    save_seen_dois(seen_path, seen)

    if metrics is not None:
        metrics.record(
            "output",
            zh=str(zh_path.relative_to(output_root)) if zh_path.is_relative_to(output_root) else str(zh_path),
            en=str(en_path.relative_to(output_root)) if llm_client is not None and en_path.is_relative_to(output_root) else None,
        )

    return zh_path


def run_pipeline(
    sources: list[SourceConfig],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
    llm_client: LLMClient | None = None,
    llm_max_items: int = 12,
    metrics: RunMetrics | None = None,
) -> Path:
    items: list[SourceItem] = []
    per_source: list[dict[str, Any]] = []
    for source in sources:
        try:
            fetched = fetch_source(source)
            items.extend(fetched)
            per_source.append({"id": source.id, "count": len(fetched)})
        except Exception as error:
            print(f"Skipping source {source.id}: {error}", file=sys.stderr)
            per_source.append({"id": source.id, "count": 0, "error": str(error)[:200]})
    if metrics is not None:
        metrics.record("fetch_total", total=len(items), sources=per_source)
    return run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=digest_config,
        digest_date=digest_date,
        template_path=template_path,
        output_root=output_root,
        llm_client=llm_client,
        llm_max_items=llm_max_items,
        metrics=metrics,
    )
