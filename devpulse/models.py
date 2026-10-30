"""Data shapes shared by retrieval, analysis and the report."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Comment(BaseModel):
    """One Hacker News comment, the only kind of evidence DevPulse uses."""

    ref: str            # short citation id shown to the model, e.g. "C3"
    hn_id: str
    author: str
    text: str
    story_title: str
    created_at: str

    @property
    def url(self) -> str:
        return f"https://news.ycombinator.com/item?id={self.hn_id}"


class Point(BaseModel):
    """A pro or con. `quote` must appear word for word in a cited comment."""

    point: str = Field(max_length=160)
    quote: str
    cites: list[str]


class Analysis(BaseModel):
    pros: list[Point] = Field(default_factory=list)
    cons: list[Point] = Field(default_factory=list)


class Rejection(BaseModel):
    side: str
    point: str
    reason: str


class Report(BaseModel):
    tool: str
    stories: list[str]
    comments: list[Comment]
    pros: list[Point]
    cons: list[Point]
    written_by: str                 # "llm" or "baseline"
    rejected: list[Rejection] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
