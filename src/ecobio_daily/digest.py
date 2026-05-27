from __future__ import annotations

from collections import OrderedDict
from datetime import date

from ecobio_daily.models import Digest, DigestSection, ScoredItem


def build_digest(
    digest_date: date,
    title: str,
    scored_items: list[ScoredItem],
    min_relevance_score: int,
    max_items: int,
    highlight_count: int,
) -> Digest:
    selected = [
        item for item in scored_items if item.relevance_score >= min_relevance_score and item.topic_scores
    ]
    selected.sort(
        key=lambda item: (
            item.llm_score if item.llm_score is not None else -1,
            item.relevance_score,
        ),
        reverse=True,
    )
    selected = selected[:max_items]

    sections_by_topic: OrderedDict[str, list[ScoredItem]] = OrderedDict()
    for item in selected:
        primary_topic = item.topic_scores[0].topic_name
        sections_by_topic.setdefault(primary_topic, []).append(item)

    sections = [
        DigestSection(title=topic_name, items=items)
        for topic_name, items in sections_by_topic.items()
    ]

    return Digest(
        date=digest_date,
        title=title,
        highlights=selected[:highlight_count],
        sections=sections,
        references=[item.item for item in selected],
    )
