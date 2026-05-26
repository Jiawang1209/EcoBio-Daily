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
    llm_score: int | None = None
    llm_brief_item: dict | None = None


class DigestSection(BaseModel):
    title: str
    items: list[ScoredItem]
    llm_brief: dict | None = None


class Digest(BaseModel):
    date: date
    title: str
    highlights: list[ScoredItem]
    sections: list[DigestSection]
    references: list[SourceItem]
