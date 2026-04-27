from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.models import Digest, DigestSection, ScoredItem, SourceItem, TopicScore
from ecobio_daily.render import render_digest


def test_render_digest_contains_sections_and_references():
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="Example Journal",
        published_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        summary="Microbial diversity was associated with stronger ecosystem resilience.",
    )
    scored = ScoredItem(
        item=item,
        relevance_score=3,
        topic_scores=[
            TopicScore(
                topic_id="soil",
                topic_name="土壤微生物",
                score=3,
                matched_keywords=["soil", "microbial"],
            )
        ],
    )
    digest = Digest(
        date=date(2026, 4, 28),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[DigestSection(title="土壤微生物", items=[scored])],
        references=[item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    assert "# EcoBio Daily - 2026-04-28" in output
    assert "## 土壤微生物" in output
    assert "## References" in output
    assert "https://example.org/paper-1" in output
