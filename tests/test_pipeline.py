import json
from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.digest import build_digest
from ecobio_daily.models import ScoredItem, SourceItem, TopicScore
from ecobio_daily.pipeline import run_pipeline, run_pipeline_from_items


def _scored_item(title: str, topic_id: str, topic_name: str, score: int) -> ScoredItem:
    item = SourceItem(
        id=title,
        title=title,
        url=f"https://example.org/{title.replace(' ', '-').lower()}",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary=f"Summary for {title}",
    )
    return ScoredItem(
        item=item,
        relevance_score=score,
        topic_scores=[
            TopicScore(
                topic_id=topic_id,
                topic_name=topic_name,
                score=score,
                matched_keywords=["soil"],
            )
        ],
    )


def test_build_digest_groups_items_and_selects_highlights():
    items = [
        _scored_item("A soil microbiome paper", "soil", "土壤微生物", 4),
        _scored_item("A biodiversity paper", "biodiversity", "生物多样性与保护", 3),
        _scored_item("A weak paper", "soil", "土壤微生物", 1),
    ]

    digest = build_digest(
        digest_date=date(2026, 4, 28),
        title="EcoBio Daily",
        scored_items=items,
        min_relevance_score=2,
        max_items=10,
        highlight_count=2,
    )

    assert digest.title == "EcoBio Daily"
    assert [item.item.title for item in digest.highlights] == [
        "A soil microbiome paper",
        "A biodiversity paper",
    ]
    assert [section.title for section in digest.sections] == [
        "土壤微生物",
        "生物多样性与保护",
    ]
    assert len(digest.references) == 2


def test_run_pipeline_from_items_writes_digest(tmp_path: Path):
    items = [
        SourceItem(
            id="paper-1",
            title="Soil microbial diversity increases drought resilience",
            url="https://example.org/paper-1",
            source="example",
            published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
            summary="The soil microbiome changed carbon cycling under drought.",
        )
    ]
    topics = [
        TopicConfig(
            id="soil",
            name="土壤微生物",
            keywords=["soil", "microbiome", "carbon cycling"],
        )
    ]
    config = DigestConfig(
        title="EcoBio Daily",
        language="zh",
        output_pattern="{year}/{month}/ecobio_digest_1d_{date}_zh.md",
        max_items=12,
        highlights=3,
        min_relevance_score=2,
        lookback_days=2,
    )

    output_path = run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=config,
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
    )

    assert output_path == tmp_path / "2026/04/ecobio_digest_1d_2026-04-28_zh.md"
    assert output_path.exists()
    assert "Soil microbial diversity" in output_path.read_text(encoding="utf-8")


def test_run_pipeline_from_items_filters_by_digest_lookback_window(tmp_path: Path):
    items = [
        SourceItem(
            id="paper-in-window",
            title="In-window soil microbiome paper",
            url="https://example.org/paper-in-window",
            source="example",
            published_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
            summary="The soil microbiome changed carbon cycling under drought.",
        ),
        SourceItem(
            id="paper-too-old",
            title="Too-old soil microbiome paper",
            url="https://example.org/paper-too-old",
            source="example",
            published_at=datetime(2026, 4, 25, 23, 59, tzinfo=timezone.utc),
            summary="The soil microbiome changed carbon cycling under drought.",
        ),
        SourceItem(
            id="paper-too-new",
            title="Too-new soil microbiome paper",
            url="https://example.org/paper-too-new",
            source="example",
            published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
            summary="The soil microbiome changed carbon cycling under drought.",
        ),
    ]
    topics = [
        TopicConfig(
            id="soil",
            name="土壤微生物",
            keywords=["soil", "microbiome", "carbon cycling"],
        )
    ]
    config = DigestConfig(
        title="EcoBio Daily",
        language="zh",
        output_pattern="{year}/{month}/ecobio_digest_1d_{date}_zh.md",
        max_items=12,
        highlights=3,
        min_relevance_score=2,
        lookback_days=2,
    )

    output_path = run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=config,
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
    )

    output = output_path.read_text(encoding="utf-8")
    assert "In-window soil microbiome paper" in output
    assert "Too-old soil microbiome paper" not in output
    assert "Too-new soil microbiome paper" not in output


def test_run_pipeline_from_items_persists_raw_and_scored_candidates(tmp_path: Path):
    items = [
        SourceItem(
            id="paper-1",
            title="Soil microbiome candidate",
            url="https://example.org/paper-1",
            source="example",
            published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
            summary="The soil microbiome changed carbon cycling under drought.",
        )
    ]
    topics = [
        TopicConfig(
            id="soil",
            name="土壤微生物",
            keywords=["soil", "microbiome", "carbon cycling"],
        )
    ]
    config = DigestConfig(
        title="EcoBio Daily",
        language="zh",
        output_pattern="{year}/{month}/ecobio_digest_1d_{date}_zh.md",
        max_items=12,
        highlights=3,
        min_relevance_score=2,
        lookback_days=2,
    )

    run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=config,
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
    )

    raw_path = tmp_path / "data/raw/2026-04-28-items.json"
    scored_path = tmp_path / "data/processed/2026-04-28-scored.json"

    assert raw_path.exists()
    assert scored_path.exists()
    raw_items = json.loads(raw_path.read_text(encoding="utf-8"))
    scored_items = json.loads(scored_path.read_text(encoding="utf-8"))
    assert raw_items[0]["title"] == "Soil microbiome candidate"
    assert scored_items[0]["relevance_score"] == 3
    assert scored_items[0]["topic_scores"][0]["matched_keywords"] == [
        "soil",
        "microbiome",
        "carbon cycling",
    ]


def test_run_pipeline_continues_when_one_source_fails(monkeypatch, tmp_path: Path):
    sources = [
        SourceConfig(
            id="bad",
            name="Bad Source",
            type="rss",
            url="https://example.org/bad.xml",
        ),
        SourceConfig(
            id="good",
            name="Good Source",
            type="rss",
            url="https://example.org/good.xml",
        ),
    ]

    def fake_fetch_source(source: SourceConfig) -> list[SourceItem]:
        if source.id == "bad":
            raise RuntimeError("source unavailable")
        return [
            SourceItem(
                id="paper-1",
                title="Soil microbial diversity increases drought resilience",
                url="https://example.org/paper-1",
                source=source.name,
                published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
                summary="The soil microbiome changed carbon cycling under drought.",
            )
        ]

    monkeypatch.setattr("ecobio_daily.pipeline.fetch_source", fake_fetch_source)

    output_path = run_pipeline(
        sources=sources,
        topics=[
            TopicConfig(
                id="soil",
                name="土壤微生物",
                keywords=["soil", "microbiome", "carbon cycling"],
            )
        ],
        digest_config=DigestConfig(
            title="EcoBio Daily",
            language="zh",
            output_pattern="{year}/{month}/ecobio_digest_1d_{date}_zh.md",
            max_items=12,
            highlights=3,
            min_relevance_score=2,
            lookback_days=2,
        ),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
    )

    assert output_path.exists()
    assert "Soil microbial diversity" in output_path.read_text(encoding="utf-8")
