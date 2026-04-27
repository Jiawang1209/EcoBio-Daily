from datetime import date, datetime, timezone

from ecobio_daily.config import TopicConfig
from ecobio_daily.models import SourceItem
from ecobio_daily.scoring import deduplicate_items, score_item


def test_source_item_normalizes_empty_summary():
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary=None,
        tags=["soil", "microbiome"],
    )

    assert item.summary == ""
    assert item.published_date == date(2026, 4, 28)


def test_score_item_matches_title_and_summary_keywords():
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="The rhizosphere microbiome changed carbon cycling under drought.",
    )
    topics = [
        TopicConfig(
            id="soil_microbiome",
            name="土壤微生物",
            keywords=["soil", "microbiome", "rhizosphere", "carbon cycling"],
        )
    ]

    scored = score_item(item, topics)

    assert scored.relevance_score == 4
    assert scored.topic_scores[0].topic_id == "soil_microbiome"
    assert scored.topic_scores[0].matched_keywords == [
        "soil",
        "microbiome",
        "rhizosphere",
        "carbon cycling",
    ]


def test_deduplicate_items_prefers_first_seen_url():
    first = SourceItem(
        id="a",
        title="Same paper",
        url="https://example.org/paper",
        source="source-a",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )
    duplicate = SourceItem(
        id="b",
        title="Same paper",
        url="https://example.org/paper",
        source="source-b",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )

    unique = deduplicate_items([first, duplicate])

    assert unique == [first]
