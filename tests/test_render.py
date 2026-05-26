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


def _scored_for_render(title: str = "Soil paper") -> ScoredItem:
    item = SourceItem(
        id=title,
        title=title,
        url=f"https://example.org/{title.replace(' ', '-')}",
        source="Example Journal",
        published_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
        summary="Original English summary about soil microbes.",
    )
    return ScoredItem(
        item=item,
        relevance_score=4,
        topic_scores=[
            TopicScore(topic_id="soil", topic_name="土壤微生物", score=4, matched_keywords=["soil"])
        ],
        llm_score=8,
    )


def test_render_uses_llm_brief_when_section_has_it():
    scored = _scored_for_render("Forest nitrogen paper")
    digest = Digest(
        date=date(2026, 5, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[
            DigestSection(
                title="土壤微生物",
                items=[scored],
                llm_brief={
                    "section_title": "森林土壤简报",
                    "highlights": ["亮点A", "亮点B", "亮点C"],
                    "items": [
                        {
                            "title": "Forest nitrogen paper",
                            "summary_zh": "中文凝练的摘要内容。",
                            "why_it_matters": "对氮循环有意义。",
                            "evidence_type": "实验",
                            "caveat": "样本有限。",
                            "source_url": "https://example.org/Forest-nitrogen-paper",
                        }
                    ],
                },
            )
        ],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    assert "森林土壤简报" in output
    assert "中文凝练的摘要内容。" in output
    assert "对氮循环有意义。" in output
    assert "实验" in output
    assert "样本有限。" in output
    assert "亮点A" in output
    # English summary only appears in doc-level Highlights (legacy), not in section body.
    body = output.split("## 森林土壤简报", 1)[1].split("## References", 1)[0]
    assert "Original English summary" not in body


def test_render_falls_back_to_summary_when_no_llm_brief():
    scored = _scored_for_render("Plain paper")
    digest = Digest(
        date=date(2026, 5, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[
            DigestSection(title="土壤微生物", items=[scored], llm_brief=None)
        ],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    assert "Original English summary about soil microbes." in output
    assert "中文凝练的摘要内容。" not in output


def test_render_highlights_uses_llm_brief_item_summary_zh():
    scored = _scored_for_render("Forest nitrogen paper")
    scored.llm_brief_item = {
        "title": "Forest nitrogen paper",
        "summary_zh": "中文版摘要-顶部高亮",
        "why_it_matters": "X",
        "evidence_type": "实验",
        "caveat": None,
        "source_url": "https://example.org/Forest-nitrogen-paper",
    }
    digest = Digest(
        date=date(2026, 5, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[DigestSection(title="土壤微生物", items=[scored])],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    highlights_block = output.split("## Highlights", 1)[1].split("##", 1)[0]
    assert "中文版摘要-顶部高亮" in highlights_block
    assert "Original English summary about soil microbes" not in highlights_block


def test_render_highlights_falls_back_when_no_llm_brief_item():
    scored = _scored_for_render("Plain paper")
    digest = Digest(
        date=date(2026, 5, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[DigestSection(title="土壤微生物", items=[scored])],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    highlights_block = output.split("## Highlights", 1)[1].split("##", 1)[0]
    assert "Original English summary about soil microbes" in highlights_block
