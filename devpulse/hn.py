"""Retrieve developer discussion about a tool from Hacker News (Algolia API, no key).

A plain comment search for "bun" also matches "bunch", so retrieval is two-step:
find the most-discussed stories whose title names the tool as a whole word, then
pull the comments from those threads.
"""
from __future__ import annotations

import html
import re

import httpx

from .models import Comment

API = "https://hn.algolia.com/api/v1/search"
TAG = re.compile(r"<[^>]+>")


def clean(raw: str) -> str:
    text = TAG.sub(" ", raw.replace("<p>", "\n"))
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def names_tool(title: str, tool: str) -> bool:
    return re.search(rf"(?<![\w.]){re.escape(tool)}(?![\w])", title, re.I) is not None


class HackerNews:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=20)

    def _search(self, **params) -> list[dict]:
        response = self.client.get(API, params=params)
        response.raise_for_status()
        return response.json().get("hits", [])

    def top_stories(self, tool: str, limit: int = 3) -> list[dict]:
        stories = self._search(query=tool, tags="story", hitsPerPage=40)
        relevant = [s for s in stories if s.get("title") and names_tool(s["title"], tool)]
        relevant.sort(key=lambda s: (s.get("num_comments") or 0), reverse=True)
        return relevant[:limit]

    def comments(self, tool: str, stories: int = 3, max_comments: int = 40) -> tuple[list[str], list[Comment]]:
        titles, collected = [], []
        for story in self.top_stories(tool, stories):
            titles.append(story["title"])
            hits = self._search(tags=f"comment,story_{story['objectID']}", hitsPerPage=100)
            for hit in hits:
                text = clean(hit.get("comment_text") or "")
                if 60 <= len(text) <= 1500:
                    collected.append((hit, text, story["title"]))
        # Prefer comments that name the tool, then longer ones (more substance).
        collected.sort(key=lambda item: (not names_tool(item[1], tool), -len(item[1])))
        comments = [
            Comment(ref=f"C{i + 1}", hn_id=hit["objectID"], author=hit.get("author") or "unknown",
                    text=text, story_title=title, created_at=(hit.get("created_at") or "")[:10])
            for i, (hit, text, title) in enumerate(collected[:max_comments])
        ]
        return titles, comments
