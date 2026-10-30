"""HTTP API for the hosted demo. The same app runs locally (uvicorn) and on Cloudflare."""
from __future__ import annotations

import re
import time
from typing import Awaitable, Callable, Protocol

from fastapi import FastAPI, HTTPException, Query

from .agent import investigate
from .llm import LLMAnalyst
from .models import Report
from .render import to_markdown

TOOL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+#_-]{0,39}$")
CACHE_SECONDS = 24 * 60 * 60


class Cache(Protocol):
    async def get(self, key: str) -> tuple[str, float] | None: ...
    async def put(self, key: str, value: str, stamp: float) -> None: ...


class MemoryCache:
    def __init__(self):
        self.items: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> tuple[str, float] | None:
        return self.items.get(key)

    async def put(self, key: str, value: str, stamp: float) -> None:
        self.items[key] = (value, stamp)


Investigate = Callable[[str], Awaitable[Report]]


def create_app(cache: Cache | None = None, run: Investigate | None = None,
               analyst_factory: Callable[[], LLMAnalyst] = LLMAnalyst) -> FastAPI:
    cache = cache or MemoryCache()
    run = run or (lambda tool: investigate(tool, analyst=analyst_factory()))
    app = FastAPI(title="DevPulse", version="1.0.0",
                  description="What do developers say about a tool? Pros and cons cited from Hacker News.")

    @app.get("/api/report")
    async def report(tool: str = Query(min_length=1, max_length=40)) -> dict:
        tool = tool.strip()
        if not TOOL_NAME.match(tool):
            raise HTTPException(422, "Use a tool or library name: letters, numbers, spaces and . + # _ -")
        key = tool.lower()
        now = time.time()
        cached = await cache.get(key)
        if cached and now - cached[1] < CACHE_SECONDS:
            result = Report.model_validate_json(cached[0])
            from_cache = True
        else:
            result = await run(tool)
            if result.comments:  # don't cache empty results; HN may just have been unreachable
                await cache.put(key, result.model_dump_json(), now)
            from_cache = False
        return {"report": result.model_dump(), "markdown": to_markdown(result), "cached": from_cache}

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True}

    return app
