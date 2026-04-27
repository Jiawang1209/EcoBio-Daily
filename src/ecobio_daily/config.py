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
