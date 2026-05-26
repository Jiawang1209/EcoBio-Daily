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

    # Title hit ("soil") weighs 2; three summary hits weigh 1 each = 5.
    assert scored.relevance_score == 5
    assert scored.topic_scores[0].topic_id == "soil_microbiome"
    assert scored.topic_scores[0].matched_keywords == [
        "soil",
        "microbiome",
        "rhizosphere",
        "carbon cycling",
    ]


def test_title_hits_weigh_more_than_summary_hits():
    title_only = SourceItem(
        id="paper-title",
        title="Soil microbiome shapes forest resilience",
        url="https://example.org/paper-title",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="Long unrelated abstract about other topics.",
    )
    summary_only = SourceItem(
        id="paper-summary",
        title="A long unrelated headline about other topics",
        url="https://example.org/paper-summary",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="Soil microbiome shapes forest resilience.",
    )
    topics = [
        TopicConfig(
            id="soil_microbiome",
            name="土壤微生物",
            keywords=["soil microbiome"],
        )
    ]

    assert (
        score_item(title_only, topics).relevance_score
        > score_item(summary_only, topics).relevance_score
    )


def test_topic_excludes_skip_topic_when_negative_term_present():
    item = SourceItem(
        id="clinical-paper",
        title="Gut microbiome and type 2 diabetes",
        url="https://example.org/clinical",
        source="PubMed",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="A clinical study on patients with diabetes.",
    )
    topics = [
        TopicConfig(
            id="environmental_microbiology",
            name="环境微生物学",
            keywords=["microbiome"],
            excludes=["diabetes", "oncology"],
        )
    ]

    scored = score_item(item, topics)

    assert scored.relevance_score == 0
    assert scored.topic_scores == []


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
