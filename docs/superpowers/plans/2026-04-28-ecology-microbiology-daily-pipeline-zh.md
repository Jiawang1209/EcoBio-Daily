# 生态学与微生物学日报流水线实施计划

> **给执行代理/工程师的要求：** 实施本计划时，必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。所有步骤使用 checkbox（`- [ ]`）追踪进度。

**目标：** 从空壳仓库搭建一个本地优先的日报生成系统，每天获取生态学与微生物学领域的最新研究进展，筛选高相关内容，并生成一篇结构清晰、可人工复核的中文 Markdown 日报。

**架构：** 第一版采用半自动 CLI 流水线。配置文件定义数据源、主题分类和日报参数；Python 模块负责抓取 RSS/资讯源、标准化条目、去重、主题打分、构建日报结构，并渲染为 `YYYY/MM/` 目录下的 Markdown 文件。LLM 总结能力先作为后续增强项预留，第一版先保证不用 API key 也能生成可检查的基础日报。

**技术栈：** Python 3.11+、`pytest`、`pydantic`、`PyYAML`、`feedparser`、`httpx`、`Jinja2`，后续可接入 OpenAI 兼容的 LLM API。

---

## 一、产品范围

第一版只做一件事：**每天生成一篇生态学与微生物学中文研究进展日报**。

日报覆盖方向：

- 生态学与全球变化
- 生物多样性与保护
- 土壤生态与生物地球化学
- 环境微生物学
- 微生物组生态学
- 生态/微生物研究方法、数据集、模型与工具

第一版暂不做：

- 网站前端
- 公众号、邮件或社媒发布
- 用户系统
- 数据库
- PDF 全文解析
- 英文日报
- 全自动 GitHub Actions
- 复杂事实核查系统

第一版的成功标准是：**本地运行一条命令，可以生成一篇结构稳定、引用保留、主题相关、可人工快速复核的中文日报。**

---

## 二、建议目录结构

需要创建如下结构：

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

各文件职责：

- `config/sources.yaml`：配置数据源，例如 bioRxiv、Nature 期刊 RSS。
- `config/topics.yaml`：配置主题分类和关键词。
- `config/digest.yaml`：配置日报标题、语言、输出路径、条目数量。
- `src/ecobio_daily/models.py`：定义统一数据模型。
- `src/ecobio_daily/config.py`：读取并校验 YAML 配置。
- `src/ecobio_daily/fetch.py`：抓取 RSS 并转换为统一条目。
- `src/ecobio_daily/scoring.py`：去重、关键词匹配、主题打分。
- `src/ecobio_daily/digest.py`：把候选条目组织成日报结构。
- `src/ecobio_daily/render.py`：使用模板渲染 Markdown。
- `src/ecobio_daily/pipeline.py`：串联完整流程。
- `scripts/run_daily.py`：命令行入口。
- `templates/digest_zh.md.j2`：中文日报模板。
- `tests/`：不依赖网络和 LLM 的本地测试。

---

## 三、实施任务

### 任务 1：初始化项目骨架

**文件：**

- 创建：`pyproject.toml`
- 创建：`README.md`
- 创建：`src/ecobio_daily/__init__.py`
- 创建：`data/.gitkeep`
- 创建：`data/cache/.gitkeep`
- 创建：`data/processed/.gitkeep`
- 创建：`data/raw/.gitkeep`

- [ ] **步骤 1：创建 `pyproject.toml`**

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

- [ ] **步骤 2：创建 `README.md`**

```markdown
# EcoBio Daily

EcoBio Daily 是一个本地优先的生态学与微生物学研究进展日报生成系统。

## 第一版能力

- 从配置的数据源抓取最新研究条目。
- 按生态学和微生物学主题进行关键词筛选。
- 选择高相关内容生成中文 Markdown 日报。
- 将日报保存到 `YYYY/MM/` 目录。

## 运行方式

```bash
python scripts/run_daily.py --date 2026-04-28
```

## 输出文件

```text
2026/04/ecobio_digest_1d_2026-04-28_zh.md
```
```

- [ ] **步骤 3：创建 Python 包标记**

`src/ecobio_daily/__init__.py` 内容：

```python
"""EcoBio Daily research digest pipeline."""
```

- [ ] **步骤 4：创建数据目录**

创建以下空文件，用于保留目录：

```text
data/.gitkeep
data/cache/.gitkeep
data/processed/.gitkeep
data/raw/.gitkeep
```

- [ ] **步骤 5：运行初始测试**

```bash
python -m pytest -q
```

预期结果：

```text
no tests ran
```

---

### 任务 2：定义统一数据模型

**文件：**

- 创建：`src/ecobio_daily/models.py`
- 创建/修改：`tests/test_scoring.py`

- [ ] **步骤 1：先写模型测试**

```python
from datetime import date, datetime, timezone

from ecobio_daily.models import SourceItem


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
```

- [ ] **步骤 2：实现 `models.py`**

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

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_scoring.py::test_source_item_normalizes_empty_summary -q
```

预期结果：

```text
1 passed
```

---

### 任务 3：配置数据源、主题和日报参数

**文件：**

- 创建：`config/sources.yaml`
- 创建：`config/topics.yaml`
- 创建：`config/digest.yaml`
- 创建：`src/ecobio_daily/config.py`
- 创建：`tests/test_config.py`

- [ ] **步骤 1：创建数据源配置**

`config/sources.yaml`：

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

- [ ] **步骤 2：创建主题配置**

`config/topics.yaml`：

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

- [ ] **步骤 3：创建日报参数配置**

`config/digest.yaml`：

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

- [ ] **步骤 4：实现配置读取器**

`src/ecobio_daily/config.py`：

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

- [ ] **步骤 5：测试配置读取**

```bash
python -m pytest tests/test_config.py -q
```

预期结果：

```text
3 passed
```

---

### 任务 4：抓取 RSS 并标准化条目

**文件：**

- 创建：`src/ecobio_daily/fetch.py`
- 创建：`tests/fixtures/sample_feed.xml`
- 创建：`tests/test_fetch.py`

- [ ] **步骤 1：创建测试 RSS fixture**

`tests/fixtures/sample_feed.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Ecology Feed</title>
    <item>
      <title>Soil microbial diversity increases drought resilience</title>
      <link>https://example.org/paper-1</link>
      <guid>paper-1</guid>
      <pubDate>Tue, 28 Apr 2026 08:00:00 GMT</pubDate>
      <description>Microbial diversity was associated with stronger ecosystem resilience under drought.</description>
    </item>
    <item>
      <title>Remote sensing reveals biodiversity loss in fragmented forests</title>
      <link>https://example.org/paper-2</link>
      <guid>paper-2</guid>
      <pubDate>Mon, 27 Apr 2026 08:00:00 GMT</pubDate>
      <description>Satellite data quantified biodiversity changes in fragmented landscapes.</description>
    </item>
  </channel>
</rss>
```

- [ ] **步骤 2：实现 RSS 解析和抓取**

`src/ecobio_daily/fetch.py`：

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

- [ ] **步骤 3：运行抓取测试**

```bash
python -m pytest tests/test_fetch.py -q
```

预期结果：

```text
1 passed
```

---

### 任务 5：去重、主题匹配和相关性打分

**文件：**

- 创建：`src/ecobio_daily/scoring.py`
- 修改：`tests/test_scoring.py`

- [ ] **步骤 1：实现打分逻辑**

`src/ecobio_daily/scoring.py`：

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

- [ ] **步骤 2：验证打分行为**

测试应覆盖：

```python
def test_score_item_matches_title_and_summary_keywords():
    ...


def test_deduplicate_items_prefers_first_seen_url():
    ...
```

预期：

```bash
python -m pytest tests/test_scoring.py -q
```

```text
3 passed
```

---

### 任务 6：构建日报结构

**文件：**

- 创建：`src/ecobio_daily/digest.py`
- 创建/修改：`tests/test_pipeline.py`

- [ ] **步骤 1：实现日报构建器**

`src/ecobio_daily/digest.py`：

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

- [ ] **步骤 2：测试分组和 Highlights**

```bash
python -m pytest tests/test_pipeline.py::test_build_digest_groups_items_and_selects_highlights -q
```

预期：

```text
1 passed
```

---

### 任务 7：渲染中文 Markdown 日报

**文件：**

- 创建：`templates/digest_zh.md.j2`
- 创建：`src/ecobio_daily/render.py`
- 创建：`tests/test_render.py`

- [ ] **步骤 1：创建中文模板**

`templates/digest_zh.md.j2`：

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

- [ ] **步骤 2：实现渲染器**

`src/ecobio_daily/render.py`：

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

- [ ] **步骤 3：运行渲染测试**

```bash
python -m pytest tests/test_render.py -q
```

预期：

```text
1 passed
```

---

### 任务 8：串联完整流水线

**文件：**

- 创建：`src/ecobio_daily/pipeline.py`
- 修改：`tests/test_pipeline.py`

- [ ] **步骤 1：实现流水线**

`src/ecobio_daily/pipeline.py`：

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

- [ ] **步骤 2：测试无网络流水线**

```bash
python -m pytest tests/test_pipeline.py -q
```

预期：

```text
2 passed
```

---

### 任务 9：创建命令行入口

**文件：**

- 创建：`scripts/run_daily.py`

- [ ] **步骤 1：实现 CLI**

`scripts/run_daily.py`：

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

- [ ] **步骤 2：运行全部测试**

```bash
python -m pytest -q
```

预期：

```text
8 passed
```

- [ ] **步骤 3：本地生成日报**

```bash
python scripts/run_daily.py --date 2026-04-28
```

预期：

```text
Wrote digest: 2026/04/ecobio_digest_1d_2026-04-28_zh.md
```

如果当前环境无法联网，则以 `run_pipeline_from_items` 的测试作为本地可运行证明。

---

### 任务 10：建立日报质量检查清单

**文件：**

- 修改：`README.md`
- 创建：`docs/digest-quality-checklist.md`

- [ ] **步骤 1：创建质量检查清单**

`docs/digest-quality-checklist.md`：

```markdown
# 日报质量检查清单

每次发布 EcoBio Daily 前，按以下清单快速复核。

## 必查项

- 日报只有一个 `## Highlights`。
- 日报只有一个 `## References`。
- 每个引用条目都有来源链接。
- 前三条 Highlights 与生态学或微生物学直接相关。
- 普通媒体新闻不能挤掉重要论文、数据集或方法工具。
- 正文区分“研究发现”“模型推测”“媒体报道”。
- 来源只报告相关性时，正文不能写成因果结论。
- 没有无来源支撑的医学、农业或气候政策建议。

## 编辑偏好

- 优先选择近期论文、预印本、数据集、方法和综述。
- 优先选择具有明确生态机制或微生物机制的研究。
- 优先选择连接野外观测、控制实验、组学、模型或遥感的跨尺度研究。
- 避免泛 AI、泛医学、泛生物技术内容，除非它们与生态学或微生物学有直接关系。
```

- [ ] **步骤 2：更新 README 的人工发布流程**

追加：

```markdown
## 人工发布流程

1. 运行生成器：

   ```bash
   python scripts/run_daily.py --date YYYY-MM-DD
   ```

2. 根据 `docs/digest-quality-checklist.md` 复核生成的 Markdown。

3. 提交日报：

   ```bash
   git add YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md
   git commit -m "Add EcoBio daily report: YYYY-MM-DD"
   ```
```

---

## 四、验收标准

实现完成后，应满足：

- `python -m pytest -q` 本地通过。
- 在可联网环境下，`python scripts/run_daily.py --date 2026-04-28` 能生成 `2026/04/ecobio_digest_1d_2026-04-28_zh.md`。
- 生成的 Markdown 至少包含 `Highlights`、主题板块、`Looking Forward` 和 `References`。
- 至少有一个测试证明：不联网也可以通过注入测试数据生成日报。
- README 说明了如何运行和人工复核。
- 质量检查清单明确体现生态学与微生物学领域偏好。

---

## 五、后续迭代

第一版连续试运行 3-5 天后，再考虑：

- 接入 LLM，让正文从“摘要拼接”升级为“凝练综述”。
- 增加 URL 缓存，避免重复报道同一条目。
- 增加 GitHub Actions 定时运行。
- 增加英文日报。
- 增加 PubMed、Crossref、Semantic Scholar、Europe PMC、期刊 RSS 和机构新闻源。
- 增加一个轻量静态首页，索引所有历史日报。

---

## 六、自检

需求覆盖：

- “每天获取最新研究进展”：由数据源配置、RSS 抓取、CLI 流水线覆盖。
- “生态学和微生物学领域”：由主题配置和质量清单覆盖。
- “凝练和总结”：第一版由结构化日报模板实现，LLM 凝练作为第二阶段增强。
- “不是空壳”：计划明确了配置、源码、模板、测试、运行命令和验收方式。

范围控制：

- 第一版不做网站、不做数据库、不做发布平台，避免过早复杂化。
- 第一版先跑通内容生产闭环，再进入自动发布和 LLM 深度改写。

一致性检查：

- 输出路径统一为 `YYYY/MM/ecobio_digest_1d_YYYY-MM-DD_zh.md`。
- 主题配置、打分逻辑、日报模板都围绕生态学与微生物学。
- 所有模块从配置到输出形成一条完整流水线。
