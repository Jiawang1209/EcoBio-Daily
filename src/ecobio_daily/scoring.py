from __future__ import annotations

from ecobio_daily.config import TopicConfig
from ecobio_daily.models import ScoredItem, SourceItem, TopicScore


def _search_text(item: SourceItem) -> str:
    return f"{item.title}\n{item.summary}".lower()


def score_item(item: SourceItem, topics: list[TopicConfig]) -> ScoredItem:
    text = _search_text(item)
    topic_scores: list[TopicScore] = []

    for topic in topics:
        matched = [keyword for keyword in topic.keywords if keyword.lower() in text]
        if matched:
            topic_scores.append(
                TopicScore(
                    topic_id=topic.id,
                    topic_name=topic.name,
                    score=len(matched),
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
