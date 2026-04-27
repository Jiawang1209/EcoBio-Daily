# Ecology Microbiology Daily Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first pipeline that gathers recent ecology and microbiology research items, filters and groups them, and generates a concise Chinese Markdown daily digest.

**Architecture:** The first version is a semi-automated CLI workflow: configuration files define sources and topics, Python modules fetch and normalize source items, filtering logic scores relevance, and a digest generator writes a Markdown report under `YYYY/MM/`. LLM integration is optional at runtime: the pipeline can render a deterministic draft without an API key, and can later use an LLM provider for higher-quality synthesis.

**Tech Stack:** Python 3.11+, `pytest`, `pydantic`, `PyYAML`, `feedparser`, `httpx`, `Jinja2`, optional OpenAI-compatible chat completion API.

---

## Product Scope

The first release focuses on one daily Chinese digest for ecology and microbiology. It should work from the command line and produce a Markdown file that is useful even before full automation.

The digest covers:

- Ecology and global change
- Biodiversity and conservation
- Soil ecology and biogeochemistry
- Environmental microbiology
- Microbiome ecology
- Methods, datasets, models, and tools

The first release does not include:

- Website frontend
- Email or WeChat publishing
- User accounts
- Database storage
- Full paper PDF parsing
- Automated claim verification beyond source link preservation
- English digest generation

## File Structure

Create these files:

```text
EcoBio-Daily/
├── README.md
├── pyproject.toml
├── config/
│   ├── digest.yaml
│   ├── sources.yaml
│   └── topics.yaml
├── data/
│   ├── .gitkeep
│   ├── cache/.gitkeep
│   ├── processed/.gitkeep
│   └── raw/.gitkeep
├── scripts/
│   └── run_daily.py
├── src/
│   └── ecobio_daily/
│       ├── __init__.py
│       ├── config.py
│       ├── digest.py
│       ├── fetch.py
│       ├── models.py
│       ├── pipeline.py
│       ├── render.py
│       └── scoring.py
├── templates/
│   └── digest_zh.md.j2
└── tests/
    ├── fixtures/
    │   └── sample_feed.xml
    ├── test_config.py
    ├── test_fetch.py
    ├── test_pipeline.py
    ├── test_render.py
    └── test_scoring.py
```

Responsibilities:

- `config/sources.yaml`: list of RSS/API/manual sources.
- `config/topics.yaml`: topic taxonomy and keywords.
- `config/digest.yaml`: output naming, language, item limits, and date handling.
- `src/ecobio_daily/models.py`: shared typed models.
- `src/ecobio_daily/config.py`: load and validate YAML config.
- `src/ecobio_daily/fetch.py`: fetch and normalize feed items.
- `src/ecobio_daily/scoring.py`: score relevance and assign topics.
- `src/ecobio_daily/render.py`: render Markdown from selected items.
- `src/ecobio_daily/digest.py`: build a structured digest object.
- `src/ecobio_daily/pipeline.py`: orchestrate fetch, score, select, and render.
- `scripts/run_daily.py`: CLI entry point.
- `templates/digest_zh.md.j2`: Chinese Markdown digest template.
- `tests/`: fast local verification without network or LLM calls.

---

### Task 1: Project Skeleton and Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/ecobio_daily/__init__.py`
- Create: `data/.gitkeep`
- Create: `data/cache/.gitkeep`
- Create: `data/processed/.gitkeep`
- Create: `data/raw/.gitkeep`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ecobio-daily"
version = "0.1.0"
description = "Daily ecology and microbiology research digest pipeline."
requires-python = ">=3.11"
dependencies = [
  "feedparser>=6.0.11",
  "httpx>=0.27.0",
  "jinja2>=3.1.4",
  "pydantic>=2.7.0",
  "pyyaml>=6.0.1"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create initial `README.md`**

```markdown
# EcoBio Daily

EcoBio Daily is a local-first pipeline for generating a concise Chinese daily digest of recent ecology and microbiology research.

## First Release Scope

- Fetch recent source items from configured RSS feeds.
- Score relevance to ecology and microbiology topics.
- Select the highest-value items for a daily digest.
- Render a Markdown report under `YYYY/MM/`.

## Run

```bash
python scripts/run_daily.py --date 2026-04-27
```

## Output

```text
2026/04/ecobio_digest_1d_2026-04-27_zh.md
```
```

- [ ] **Step 3: Create package marker**

```python
"""EcoBio Daily research digest pipeline."""
```

- [ ] **Step 4: Create data directories**

Create empty `.gitkeep` files at:

```text
data/.gitkeep
data/cache/.gitkeep
data/processed/.gitkeep
data/raw/.gitkeep
```

- [ ] **Step 5: Run initial test command**

Run:

```bash
python -m pytest -q
```

Expected:

```text
no tests ran
```

- [ ] **Step 6: Commit**

```bash
git add README.md pyproject.toml src/ecobio_daily/__init__.py data
git commit -m "chore: initialize ecobio daily project"
```

---

### Task 2: Typed Models

**Files:**
- Create: `src/ecobio_daily/models.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: Write model smoke test**

```python
from datetime import date, datetime, timezone

from ecobio_daily.models import SourceItem


def test_source_item_normalizes_empty_summary():
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="example",
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        summary=None,
        tags=["soil", "microbiome"],
    )

    assert item.summary == ""
    assert item.published_date == date(2026, 4, 27)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_scoring.py::test_source_item_normalizes_empty_summary -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.models'
```

- [ ] **Step 3: Implement models**

```python
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class SourceItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str = ""
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: str | None) -> str:
        return value or ""

    @property
    def published_date(self) -> date:
        return self.published_at.date()


class TopicScore(BaseModel):
    topic_id: str
    topic_name: str
    score: int
    matched_keywords: list[str] = Field(default_factory=list)


class ScoredItem(BaseModel):
    item: SourceItem
    relevance_score: int
    topic_scores: list[TopicScore]


class DigestSection(BaseModel):
    title: str
    items: list[ScoredItem]


class Digest(BaseModel):
    date: date
    title: str
    highlights: list[ScoredItem]
    sections: list[DigestSection]
    references: list[SourceItem]
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_scoring.py::test_source_item_normalizes_empty_summary -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/ecobio_daily/models.py tests/test_scoring.py
git commit -m "feat: add digest data models"
```

---

### Task 3: Configuration Files and Loader

**Files:**
- Create: `config/sources.yaml`
- Create: `config/topics.yaml`
- Create: `config/digest.yaml`
- Create: `src/ecobio_daily/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Create `config/sources.yaml`**

```yaml
sources:
  - id: bioarxiv_ecology
    name: bioRxiv Ecology
    type: rss
    url: https://connect.biorxiv.org/biorxiv_xml.php?subject=ecology
  - id: bioarxiv_microbiology
    name: bioRxiv Microbiology
    type: rss
    url: https://connect.biorxiv.org/biorxiv_xml.php?subject=microbiology
  - id: nature_ecology
    name: Nature Ecology & Evolution
    type: rss
    url: https://www.nature.com/natecolevol.rss
```

- [ ] **Step 2: Create `config/topics.yaml`**

```yaml
topics:
  - id: biodiversity_conservation
    name: 生物多样性与保护
    keywords:
      - biodiversity
      - conservation
      - species richness
      - ecosystem services
      - protected area
      - extinction
  - id: soil_microbiome_biogeochemistry
    name: 土壤微生物与生物地球化学
    keywords:
      - soil microbiome
      - microbial community
      - biogeochemistry
      - carbon cycling
      - nitrogen cycling
      - rhizosphere
  - id: global_change_ecology
    name: 全球变化生态学
    keywords:
      - climate change
      - warming
      - drought
      - precipitation
      - land use
      - disturbance
  - id: environmental_microbiology
    name: 环境微生物学
    keywords:
      - environmental microbiology
      - metagenomics
      - microbial ecology
      - antibiotic resistance
      - pathogen
      - biofilm
  - id: methods_models_tools
    name: 方法、模型与数据工具
    keywords:
      - remote sensing
      - machine learning
      - model
      - dataset
      - pipeline
      - database
```

- [ ] **Step 3: Create `config/digest.yaml`**

```yaml
digest:
  title: EcoBio Daily
  language: zh
  output_pattern: "{year}/{month}/ecobio_digest_1d_{date}_zh.md"
  max_items: 12
  highlights: 3
  min_relevance_score: 2
  lookback_days: 2
```

- [ ] **Step 4: Write failing config test**

```python
from pathlib import Path

from ecobio_daily.config import load_digest_config, load_sources, load_topics


def test_load_sources_from_yaml(tmp_path: Path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - id: example
    name: Example Feed
    type: rss
    url: https://example.org/feed.xml
""".strip(),
        encoding="utf-8",
    )

    sources = load_sources(path)

    assert sources[0].id == "example"
    assert sources[0].type == "rss"


def test_load_topics_from_yaml(tmp_path: Path):
    path = tmp_path / "topics.yaml"
    path.write_text(
        """
topics:
  - id: soil
    name: 土壤生态
    keywords:
      - soil
      - rhizosphere
""".strip(),
        encoding="utf-8",
    )

    topics = load_topics(path)

    assert topics[0].name == "土壤生态"
    assert topics[0].keywords == ["soil", "rhizosphere"]


def test_load_digest_config_from_yaml(tmp_path: Path):
    path = tmp_path / "digest.yaml"
    path.write_text(
        """
digest:
  title: EcoBio Daily
  language: zh
  output_pattern: "{year}/{month}/ecobio_digest_1d_{date}_zh.md"
  max_items: 12
  highlights: 3
  min_relevance_score: 2
  lookback_days: 2
""".strip(),
        encoding="utf-8",
    )

    config = load_digest_config(path)

    assert config.title == "EcoBio Daily"
    assert config.highlights == 3
```

- [ ] **Step 5: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_config.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.config'
```

- [ ] **Step 6: Implement config loader**

```python
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, HttpUrl


class SourceConfig(BaseModel):
    id: str
    name: str
    type: str
    url: HttpUrl


class TopicConfig(BaseModel):
    id: str
    name: str
    keywords: list[str]


class DigestConfig(BaseModel):
    title: str
    language: str
    output_pattern: str
    max_items: int
    highlights: int
    min_relevance_score: int
    lookback_days: int


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def load_sources(path: Path) -> list[SourceConfig]:
    data = _load_yaml(path)
    return [SourceConfig.model_validate(source) for source in data.get("sources", [])]


def load_topics(path: Path) -> list[TopicConfig]:
    data = _load_yaml(path)
    return [TopicConfig.model_validate(topic) for topic in data.get("topics", [])]


def load_digest_config(path: Path) -> DigestConfig:
    data = _load_yaml(path)
    return DigestConfig.model_validate(data["digest"])
```

- [ ] **Step 7: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_config.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Commit**

```bash
git add config src/ecobio_daily/config.py tests/test_config.py
git commit -m "feat: add digest configuration"
```

---

### Task 4: RSS Fetching and Normalization

**Files:**
- Create: `src/ecobio_daily/fetch.py`
- Create: `tests/fixtures/sample_feed.xml`
- Test: `tests/test_fetch.py`

- [ ] **Step 1: Create feed fixture**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Ecology Feed</title>
    <item>
      <title>Soil microbial diversity increases drought resilience</title>
      <link>https://example.org/paper-1</link>
      <guid>paper-1</guid>
      <pubDate>Mon, 27 Apr 2026 08:00:00 GMT</pubDate>
      <description>Microbial diversity was associated with stronger ecosystem resilience under drought.</description>
    </item>
    <item>
      <title>Remote sensing reveals biodiversity loss in fragmented forests</title>
      <link>https://example.org/paper-2</link>
      <guid>paper-2</guid>
      <pubDate>Sun, 26 Apr 2026 08:00:00 GMT</pubDate>
      <description>Satellite data quantified biodiversity changes in fragmented landscapes.</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write failing fetch test**

```python
from pathlib import Path

from ecobio_daily.fetch import parse_rss


def test_parse_rss_fixture():
    xml = Path("tests/fixtures/sample_feed.xml").read_text(encoding="utf-8")

    items = parse_rss(xml, source_id="sample", source_name="Sample Feed")

    assert len(items) == 2
    assert items[0].id == "paper-1"
    assert items[0].source == "Sample Feed"
    assert items[0].title == "Soil microbial diversity increases drought resilience"
    assert items[0].summary.startswith("Microbial diversity")
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_fetch.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.fetch'
```

- [ ] **Step 4: Implement fetcher**

```python
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from ecobio_daily.config import SourceConfig
from ecobio_daily.models import SourceItem


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_rss(xml: str, source_id: str, source_name: str) -> list[SourceItem]:
    feed = feedparser.parse(xml)
    items: list[SourceItem] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        item_id = entry.get("id") or entry.get("guid") or url
        item = SourceItem(
            id=str(item_id),
            title=entry.get("title", "").strip(),
            url=url,
            source=source_name,
            published_at=_parse_datetime(entry.get("published")),
            summary=entry.get("summary", ""),
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def fetch_source(source: SourceConfig, timeout_seconds: float = 20.0) -> list[SourceItem]:
    if source.type != "rss":
        raise ValueError(f"Unsupported source type: {source.type}")
    response = httpx.get(str(source.url), timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    return parse_rss(response.text, source_id=source.id, source_name=source.name)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_fetch.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add src/ecobio_daily/fetch.py tests/fixtures/sample_feed.xml tests/test_fetch.py
git commit -m "feat: add rss fetching"
```

---

### Task 5: Relevance Scoring and Topic Assignment

**Files:**
- Create: `src/ecobio_daily/scoring.py`
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Add scoring tests**

```python
from datetime import datetime, timezone

from ecobio_daily.config import TopicConfig
from ecobio_daily.models import SourceItem
from ecobio_daily.scoring import deduplicate_items, score_item


def test_score_item_matches_title_and_summary_keywords():
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="example",
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
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
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    duplicate = SourceItem(
        id="b",
        title="Same paper",
        url="https://example.org/paper",
        source="source-b",
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )

    unique = deduplicate_items([first, duplicate])

    assert unique == [first]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_scoring.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.scoring'
```

- [ ] **Step 3: Implement scoring**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_scoring.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/ecobio_daily/scoring.py tests/test_scoring.py
git commit -m "feat: score ecology microbiology relevance"
```

---

### Task 6: Digest Builder

**Files:**
- Create: `src/ecobio_daily/digest.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write digest builder test**

```python
from datetime import date, datetime, timezone

from ecobio_daily.models import ScoredItem, SourceItem, TopicScore
from ecobio_daily.digest import build_digest


def _scored_item(title: str, topic_id: str, topic_name: str, score: int) -> ScoredItem:
    item = SourceItem(
        id=title,
        title=title,
        url=f"https://example.org/{title.replace(' ', '-').lower()}",
        source="example",
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
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
        digest_date=date(2026, 4, 27),
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_pipeline.py::test_build_digest_groups_items_and_selects_highlights -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.digest'
```

- [ ] **Step 3: Implement digest builder**

```python
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
    selected.sort(key=lambda item: item.relevance_score, reverse=True)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_pipeline.py::test_build_digest_groups_items_and_selects_highlights -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/ecobio_daily/digest.py tests/test_pipeline.py
git commit -m "feat: build structured daily digest"
```

---

### Task 7: Markdown Rendering

**Files:**
- Create: `templates/digest_zh.md.j2`
- Create: `src/ecobio_daily/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Create Chinese digest template**

```jinja
# {{ digest.title }} - {{ digest.date.isoformat() }}

> 生态学与微生物学最新研究进展日报。内容由配置源抓取、主题筛选和自动摘要生成，建议发布前人工快速复核。

## Highlights

{% for item in digest.highlights -%}
- **{{ item.item.title }}**：{{ item.item.summary | default("", true) | truncate(180) }} 来源：{{ item.item.source }}。
{% endfor %}

{% for section in digest.sections %}
## {{ section.title }}

{% for scored in section.items -%}
### {{ scored.item.title }}

{{ scored.item.summary | default("暂无摘要。", true) }}

- 来源：{{ scored.item.source }}
- 链接：{{ scored.item.url }}
- 相关性评分：{{ scored.relevance_score }}
- 命中关键词：{{ scored.topic_scores[0].matched_keywords | join(", ") }}

{% endfor %}
{% endfor %}
## Looking Forward

今天的候选内容显示，生态学与微生物学研究正在围绕环境变化响应、微生物群落功能、生物多样性监测和数据驱动方法持续推进。后续值得重点跟踪跨尺度观测、长期实验数据、微生物机制解释和可复用分析工具。

## References

{% for item in digest.references -%}
- **{{ item.title }}** — [{{ item.source }}]({{ item.url }})
{% endfor %}
```

- [ ] **Step 2: Write rendering test**

```python
from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.models import Digest, DigestSection, ScoredItem, SourceItem, TopicScore
from ecobio_daily.render import render_digest


def test_render_digest_contains_sections_and_references(tmp_path: Path):
    item = SourceItem(
        id="paper-1",
        title="Soil microbial diversity increases drought resilience",
        url="https://example.org/paper-1",
        source="Example Journal",
        published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
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
        date=date(2026, 4, 27),
        title="EcoBio Daily",
        highlights=[scored],
        sections=[DigestSection(title="土壤微生物", items=[scored])],
        references=[item],
    )

    output = render_digest(digest, Path("templates/digest_zh.md.j2"))

    assert "# EcoBio Daily - 2026-04-27" in output
    assert "## 土壤微生物" in output
    assert "## References" in output
    assert "https://example.org/paper-1" in output
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_render.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'ecobio_daily.render'
```

- [ ] **Step 4: Implement renderer**

```python
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ecobio_daily.models import Digest


def render_digest(digest: Digest, template_path: Path) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    return template.render(digest=digest).strip() + "\n"
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_render.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add templates/digest_zh.md.j2 src/ecobio_daily/render.py tests/test_render.py
git commit -m "feat: render chinese markdown digest"
```

---

### Task 8: Pipeline Orchestration

**Files:**
- Create: `src/ecobio_daily/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add pipeline test with injected items**

```python
from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.config import DigestConfig, TopicConfig
from ecobio_daily.models import SourceItem
from ecobio_daily.pipeline import run_pipeline_from_items


def test_run_pipeline_from_items_writes_digest(tmp_path: Path):
    items = [
        SourceItem(
            id="paper-1",
            title="Soil microbial diversity increases drought resilience",
            url="https://example.org/paper-1",
            source="example",
            published_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
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
        digest_date=date(2026, 4, 27),
        template_path=Path("templates/digest_zh.md.j2"),
        output_root=tmp_path,
    )

    assert output_path == tmp_path / "2026/04/ecobio_digest_1d_2026-04-27_zh.md"
    assert output_path.exists()
    assert "Soil microbial diversity" in output_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_pipeline.py::test_run_pipeline_from_items_writes_digest -q
```

Expected:

```text
ImportError: cannot import name 'run_pipeline_from_items'
```

- [ ] **Step 3: Implement pipeline orchestration**

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

from ecobio_daily.config import DigestConfig, SourceConfig, TopicConfig
from ecobio_daily.digest import build_digest
from ecobio_daily.fetch import fetch_source
from ecobio_daily.models import SourceItem
from ecobio_daily.render import render_digest
from ecobio_daily.scoring import deduplicate_items, score_item


def _output_path(output_root: Path, pattern: str, digest_date: date) -> Path:
    relative = pattern.format(
        year=f"{digest_date.year:04d}",
        month=f"{digest_date.month:02d}",
        date=digest_date.isoformat(),
    )
    return output_root / relative


def run_pipeline_from_items(
    items: list[SourceItem],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
) -> Path:
    unique_items = deduplicate_items(items)
    scored_items = [score_item(item, topics) for item in unique_items]
    digest = build_digest(
        digest_date=digest_date,
        title=digest_config.title,
        scored_items=scored_items,
        min_relevance_score=digest_config.min_relevance_score,
        max_items=digest_config.max_items,
        highlight_count=digest_config.highlights,
    )
    markdown = render_digest(digest, template_path)
    output_path = _output_path(output_root, digest_config.output_pattern, digest_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def run_pipeline(
    sources: list[SourceConfig],
    topics: list[TopicConfig],
    digest_config: DigestConfig,
    digest_date: date,
    template_path: Path,
    output_root: Path,
) -> Path:
    items: list[SourceItem] = []
    for source in sources:
        items.extend(fetch_source(source))
    return run_pipeline_from_items(
        items=items,
        topics=topics,
        digest_config=digest_config,
        digest_date=digest_date,
        template_path=template_path,
        output_root=output_root,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_pipeline.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add src/ecobio_daily/pipeline.py tests/test_pipeline.py
git commit -m "feat: orchestrate daily digest pipeline"
```

---

### Task 9: CLI Entrypoint

**Files:**
- Create: `scripts/run_daily.py`
- Test: run CLI manually after unit tests pass

- [ ] **Step 1: Create CLI script**

```python
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ecobio_daily.config import load_digest_config, load_sources, load_topics
from ecobio_daily.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate EcoBio Daily Markdown digest.")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD format.")
    parser.add_argument("--output-root", default=".", help="Directory where the report is written.")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--topics", default="config/topics.yaml")
    parser.add_argument("--digest", default="config/digest.yaml")
    parser.add_argument("--template", default="templates/digest_zh.md.j2")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)
    output_path = run_pipeline(
        sources=load_sources(Path(args.sources)),
        topics=load_topics(Path(args.topics)),
        digest_config=load_digest_config(Path(args.digest)),
        digest_date=digest_date,
        template_path=Path(args.template),
        output_root=Path(args.output_root),
    )
    print(f"Wrote digest: {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

Run:

```bash
python -m pytest -q
```

Expected:

```text
8 passed
```

- [ ] **Step 3: Run CLI with live network**

Run:

```bash
python scripts/run_daily.py --date 2026-04-27
```

Expected:

```text
Wrote digest: 2026/04/ecobio_digest_1d_2026-04-27_zh.md
```

If network access is unavailable, skip this step and use the injected-item test from Task 8 as the local proof.

- [ ] **Step 4: Inspect generated Markdown**

Run:

```bash
sed -n '1,160p' 2026/04/ecobio_digest_1d_2026-04-27_zh.md
```

Expected:

```text
# EcoBio Daily - 2026-04-27
...
## Highlights
...
## References
```

- [ ] **Step 5: Commit**

```bash
git add scripts/run_daily.py 2026/04/ecobio_digest_1d_2026-04-27_zh.md
git commit -m "feat: add daily digest cli"
```

---

### Task 10: Quality Gate for Daily Content

**Files:**
- Modify: `README.md`
- Create: `docs/digest-quality-checklist.md`

- [ ] **Step 1: Create quality checklist**

```markdown
# Digest Quality Checklist

Use this checklist before publishing each generated EcoBio Daily issue.

## Required Checks

- The digest has exactly one `## Highlights` section.
- The digest has exactly one `## References` section.
- Every referenced item has a working source URL.
- The top three highlights are relevant to ecology or microbiology.
- Media or industry news does not displace peer-reviewed or preprint research unless it is clearly important.
- The report distinguishes observed findings from speculation.
- The text does not claim causality when the source only reports association.
- The report does not include medical, agricultural, or climate policy recommendations without source support.

## Editorial Preference

- Prefer recent papers, datasets, methods, and reviews.
- Prefer items with clear ecological or microbiological mechanisms.
- Prefer cross-scale work connecting field observation, experiment, omics, modeling, or remote sensing.
- Avoid generic AI, generic medicine, and generic biotechnology unless the ecological or microbiological link is direct.
```

- [ ] **Step 2: Update README with manual workflow**

Append:

```markdown
## Manual Publishing Workflow

1. Run the generator:

   ```bash
   python scripts/run_daily.py --date YYYY-MM-DD
   ```

2. Review the generated Markdown using `docs/digest-quality-checklist.md`.

3. Commit the report:

   ```bash
   git add YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md
   git commit -m "Add EcoBio daily report: YYYY-MM-DD"
   ```
```

- [ ] **Step 3: Verify Markdown files exist**

Run:

```bash
test -f README.md
test -f docs/digest-quality-checklist.md
```

Expected:

```text
no output
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/digest-quality-checklist.md
git commit -m "docs: add digest publishing checklist"
```

---

## Acceptance Criteria

The implementation is complete when:

- `python -m pytest -q` passes locally.
- `python scripts/run_daily.py --date 2026-04-27` writes `2026/04/ecobio_digest_1d_2026-04-27_zh.md` when network access is available.
- The generated Markdown contains `Highlights`, topical sections, `Looking Forward`, and `References`.
- At least one unit test proves the pipeline can generate a digest without network access.
- The README explains how to run and review the daily digest.
- The quality checklist exists and is specific to ecology and microbiology.

## Future Iterations

After this plan is implemented and the digest quality is acceptable for 3-5 trial days, add:

- LLM synthesis with a provider abstraction and API key from environment variables.
- JSON cache of previously seen source URLs.
- GitHub Actions scheduled run.
- English digest generation.
- More sources: PubMed, Crossref, Semantic Scholar, Europe PMC, journal RSS feeds, and manually curated institutional feeds.
- A lightweight static index page listing all generated reports.

## Self-Review

Spec coverage:

- Daily research progress collection is covered by RSS source configuration and fetcher tasks.
- Ecology and microbiology scope is covered by topic configuration and quality checklist.
- Content condensation is covered by digest builder and Markdown renderer.
- Reviewability is covered by deterministic tests and the quality checklist.
- Automation path is covered by CLI first, GitHub Actions deferred to a future iteration.

Placeholder scan:

- No `TBD`, `TODO`, or vague implementation-only placeholders remain.
- Future iterations are explicitly out of first-release scope.

Type consistency:

- `SourceItem`, `ScoredItem`, `TopicScore`, `DigestSection`, and `Digest` are introduced before they are used.
- `DigestConfig`, `TopicConfig`, and `SourceConfig` names are consistent across config, scoring, pipeline, and CLI tasks.
- The output path pattern is consistently `{year}/{month}/ecobio_digest_1d_{date}_zh.md`.
