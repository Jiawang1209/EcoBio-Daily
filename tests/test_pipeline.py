import json
from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.digest import build_digest
from ecobio_daily.models import ScoredItem, SourceItem, TopicScore
from ecobio_daily.pipeline import run_pipeline, run_pipeline_from_items


_FAKE_CLIENT = object()


def _soil_item(slug: str, suffix: str = "") -> SourceItem:
    return SourceItem(
        id=slug,
        title=f"Soil microbiome {slug} {suffix}".strip(),
        url=f"https://example.org/{slug}",
        source="example",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="Soil microbial communities drive carbon cycling under drought.",
    )


def _digest_config() -> DigestConfig:
    return DigestConfig(
        title="EcoBio Daily",
        language="zh",
        output_pattern="{year}/{month}/ecobio_digest_1d_{date}_zh.md",
        max_items=12,
        highlights=3,
        min_relevance_score=2,
        lookback_days=2,
    )


def _soil_topics() -> list[TopicConfig]:
    return [
        TopicConfig(
            id="soil",
            name="土壤微生物",
            keywords=["soil", "microbiome", "carbon cycling"],
        )
    ]


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
    # Two title hits ("soil", "microbiome") at weight 2 plus one summary hit
    # ("carbon cycling") at weight 1.
    assert scored_items[0]["relevance_score"] == 5
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


def test_scored_item_llm_score_defaults_to_none():
    item = _soil_item("p1")
    scored = ScoredItem(item=item, relevance_score=5, topic_scores=[])
    assert scored.llm_score is None


def test_scored_item_accepts_explicit_llm_score():
    item = _soil_item("p1")
    scored = ScoredItem(item=item, relevance_score=5, topic_scores=[], llm_score=8)
    assert scored.llm_score == 8


def test_pipeline_skips_llm_scoring_when_client_is_none(tmp_path: Path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("batch_score should not be called when llm_client is None")

    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", fail_if_called)

    output_path = run_pipeline_from_items(
        items=[_soil_item("p1")],
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=None,
    )

    assert "Soil microbiome p1" in output_path.read_text(encoding="utf-8")


def test_pipeline_drops_items_with_low_llm_score(tmp_path: Path, monkeypatch):
    items = [_soil_item("good1"), _soil_item("bad"), _soil_item("good2")]

    captured: dict = {}

    def fake_batch_score(items_arg, client):
        captured["titles"] = [it.title for it in items_arg]
        return [9, 3, 8]  # bad below threshold of 6

    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", fake_batch_score)
    monkeypatch.setattr(
        "ecobio_daily.pipeline.generate_section", lambda *a, **kw: None
    )

    output_path = run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=_FAKE_CLIENT,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "Soil microbiome good1" in text
    assert "Soil microbiome good2" in text
    assert "Soil microbiome bad" not in text
    assert len(captured["titles"]) == 3


def test_pipeline_falls_back_when_llm_returns_all_minus_one(tmp_path: Path, monkeypatch):
    items = [_soil_item("a"), _soil_item("b")]

    def fake_batch_score(items_arg, client):
        return [-1] * len(items_arg)

    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", fake_batch_score)
    monkeypatch.setattr(
        "ecobio_daily.pipeline.generate_section", lambda *a, **kw: None
    )

    output_path = run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=_FAKE_CLIENT,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "Soil microbiome a" in text
    assert "Soil microbiome b" in text


def test_pipeline_only_scores_top_n_keyword_items(tmp_path: Path, monkeypatch):
    items = [_soil_item(f"p{i}") for i in range(6)]

    seen: dict = {"count": 0}

    def fake_batch_score(items_arg, client):
        seen["count"] = len(items_arg)
        return [9] * len(items_arg)

    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", fake_batch_score)
    monkeypatch.setattr(
        "ecobio_daily.pipeline.generate_section", lambda *a, **kw: None
    )

    run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=_FAKE_CLIENT,
        llm_max_items=3,
    )

    assert seen["count"] == 3


def _fake_brief(topic_name: str, items_arg, client):
    return {
        "section_title": f"LLM-{topic_name}",
        "highlights": ["要点1", "要点2", "要点3"],
        "items": [
            {
                "title": it.item.title,
                "summary_zh": f"中文摘要-{it.item.title}",
                "why_it_matters": "值得关注",
                "evidence_type": "实验",
                "caveat": None,
                "source_url": it.item.url,
            }
            for it in items_arg
        ],
    }


def test_pipeline_attaches_llm_brief_to_sections(tmp_path: Path, monkeypatch):
    items = [_soil_item("p1"), _soil_item("p2")]
    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", lambda its, c: [9, 9])
    monkeypatch.setattr("ecobio_daily.pipeline.generate_section", _fake_brief)

    output_path = run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=_FAKE_CLIENT,
    )

    text = output_path.read_text(encoding="utf-8")
    assert "中文摘要-Soil microbiome p1" in text
    assert "LLM-土壤微生物" in text


def test_pipeline_falls_back_per_section_when_brief_is_none(tmp_path: Path, monkeypatch):
    items = [_soil_item("p1")]
    monkeypatch.setattr("ecobio_daily.pipeline.batch_score", lambda its, c: [9])
    monkeypatch.setattr(
        "ecobio_daily.pipeline.generate_section",
        lambda topic, items_arg, client: None,
    )

    output_path = run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=_FAKE_CLIENT,
    )

    text = output_path.read_text(encoding="utf-8")
    # Falls back to original English summary
    assert "Soil microbial communities drive carbon cycling" in text


def test_pipeline_skips_brief_when_client_is_none(tmp_path: Path, monkeypatch):
    items = [_soil_item("p1")]

    def fail_if_called(*args, **kwargs):
        raise AssertionError("generate_section should not be called")

    monkeypatch.setattr("ecobio_daily.pipeline.generate_section", fail_if_called)

    output_path = run_pipeline_from_items(
        items=items,
        topics=_soil_topics(),
        digest_config=_digest_config(),
        digest_date=date(2026, 4, 28),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
        llm_client=None,
    )

    assert "Soil microbiome p1" in output_path.read_text(encoding="utf-8")
