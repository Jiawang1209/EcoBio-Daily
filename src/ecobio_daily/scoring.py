from __future__ import annotations

from ecobio_daily.config import TopicConfig
from ecobio_daily.models import ScoredItem, SourceItem, TopicScore


TITLE_WEIGHT = 2
SUMMARY_WEIGHT = 1


def score_item(item: SourceItem, topics: list[TopicConfig]) -> ScoredItem:
    title = item.title.lower()
    summary = item.summary.lower()
    combined = f"{title}\n{summary}"
    topic_scores: list[TopicScore] = []

    for topic in topics:
        if any(exclude.lower() in combined for exclude in topic.excludes):
            continue
        matched: list[str] = []
        score = 0
        for keyword in topic.keywords:
            needle = keyword.lower()
            if needle in title:
                score += TITLE_WEIGHT
                matched.append(keyword)
            elif needle in summary:
                score += SUMMARY_WEIGHT
                matched.append(keyword)
        if matched:
            topic_scores.append(
                TopicScore(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    score=score,
                    matched_keywords=matched,
                )
            )

    relevance_score = sum(topic.score for topic in topic_scores)
    topic_scores.sort(key=lambda score: score.score, reverse=True)
    return ScoredItem(item=item, relevance_score=relevance_score, topic_scores=topic_scores)


def deduplicate_items(items: list[SourceItem]) -> list[SourceItem]:
    seen: set[str] = set()
    unique: list[SourceItem] = []
    for item in items:
        key = item.url.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
