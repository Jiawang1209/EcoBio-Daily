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
    scored.llm_brief_item = {
        "title": "Forest nitrogen paper",
        "summary_zh": "中文凝练的摘要内容。",
        "why_it_matters": "对氮循环有意义。",
        "evidence_type": "实验",
        "caveat": "样本有限。",
        "source_url": "https://example.org/Forest-nitrogen-paper",
    }
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


def test_render_zh_uses_title_zh_when_present():
    scored = _scored_for_render("Forest nitrogen paper")
    scored.llm_brief_item = {
        "title": "Forest nitrogen paper",
        "title_zh": "森林氮循环新机制",
        "summary_zh": "中文摘要。",
        "why_it_matters": "重要。",
        "evidence_type": "实验",
        "caveat": None,
        "source_url": "https://example.org/Forest-nitrogen-paper",
    }
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
                    "highlights": ["a", "b", "c"],
                    "items": [scored.llm_brief_item],
                },
            )
        ],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    # Section body shows Chinese title
    body = output.split("## 森林土壤简报", 1)[1].split("## References", 1)[0]
    assert "森林氮循环新机制" in body
    # References section keeps the authoritative English title
    refs = output.split("## References", 1)[1]
    assert "Forest nitrogen paper" in refs


def test_render_zh_shows_warning_when_grounding_fails():
    scored = _scored_for_render("Suspect paper")
    scored.llm_brief_item = {
        "title": "Suspect paper",
        "title_zh": "可疑论文",
        "summary_zh": "包含未验证数字的中文摘要。",
        "why_it_matters": "X",
        "evidence_type": "实验",
        "caveat": None,
        "source_url": "https://example.org/Suspect-paper",
    }
    scored.llm_grounding = {
        "grounded": False,
        "score": 3,
        "reason": "数字与英文摘要不对应",
    }
    digest = Digest(
        date=date(2026, 5, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[
            DigestSection(
                title="土壤微生物",
                items=[scored],
                llm_brief={
                    "section_title": "土壤微生物",
                    "highlights": ["a", "b", "c"],
                    "items": [scored.llm_brief_item],
                },
            )
        ],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    body = output.split("## 土壤微生物", 1)[1].split("## References", 1)[0]
    assert "⚠️" in body
    assert "未通过事实核查" in body
    assert "数字与英文摘要不对应" in body
    # Falls back to original English abstract; suppresses Chinese fields
    assert "Original English summary about soil microbes" in body
    assert "包含未验证数字的中文摘要" not in body


def test_render_en_uses_original_english():
    scored = _scored_for_render("Forest nitrogen paper")
    scored.llm_brief_item = {
        "title": "Forest nitrogen paper",
        "title_zh": "森林氮循环新机制",
        "summary_zh": "中文摘要。",
        "why_it_matters": "重要。",
        "evidence_type": "实验",
        "caveat": None,
        "source_url": "https://example.org/Forest-nitrogen-paper",
    }
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
                    "highlights": ["a", "b", "c"],
                    "items": [scored.llm_brief_item],
                },
            )
        ],
        references=[scored.item],
    )

    output = render_digest(digest, Path("templates/digest_en.md.j2"))

    # English version uses original title and abstract
    assert "Forest nitpgen paper".replace("p", "p") in output or "Forest nitrogen paper" in output
    assert "Original English summary about soil microbes" in output
    # No Chinese-only fields leak through
    assert "森林氮循环新机制" not in output
    assert "中文摘要" not in output
    assert "为什么值得关注" not in output
    assert "证据类型" not in output
