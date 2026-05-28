from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl


class SourceConfig(BaseModel):
    id: str
    name: str
    type: str
    url: HttpUrl | None = None
    query: str | None = None
    issn: str | None = None
    max_results: int = 50


class TopicConfig(BaseModel):
    id: str
    name: str
    keywords: list[str]
    excludes: list[str] = Field(default_factory=list)


class DigestConfig(BaseModel):
    title: str
    language: str
    output_pattern: str
    max_items: int
    highlights: int
    min_relevance_score: int
    lookback_days: int
    target_items_min: int = 5


class LLMProfile(BaseModel):
    provider: str
    base_url: HttpUrl
    model: str
    api_key_env: str
    temperature: float = 0.2
    max_tokens: int = 2000
    timeout_seconds: int = 60


class LLMBudget(BaseModel):
    max_items_per_run: int = 12
    cache_llm_outputs: bool = False
    cache_dir: str = "data/cache/llm"


class LLMConfig(BaseModel):
    enabled: bool = False
    active_profile: str
    profiles: dict[str, LLMProfile]
    routing: dict[str, str | None] = Field(default_factory=dict)
    budget: LLMBudget = Field(default_factory=LLMBudget)


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


def load_llm_config(path: Path) -> LLMConfig:
    data = _load_yaml(path)
    return LLMConfig.model_validate(data["llm"])
