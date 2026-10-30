"""Cloudflare Python Worker entry point.

Static files in public/ are served by Workers Assets; /api/* runs the FastAPI app.
Reports are cached in D1 for 24 hours so repeat lookups don't spend model quota.
The OpenRouter key is a Worker secret (`wrangler secret put OPENROUTER_API_KEY`).
"""
from workers import WorkerEntrypoint

from devpulse.llm import LLMAnalyst
from devpulse.web import create_app

SCHEMA = "create table if not exists reports (tool text primary key, body text not null, stamp real not null)"


class D1Cache:
    def __init__(self, db):
        self.db = db
        self.ready = False

    async def _setup(self):
        if not self.ready:
            await self.db.prepare(SCHEMA).run()
            self.ready = True

    async def get(self, key):
        await self._setup()
        rows = (await self.db.prepare("select body, stamp from reports where tool = ?").bind(key).all()).results
        return (rows[0]["body"], rows[0]["stamp"]) if rows else None

    async def put(self, key, value, stamp):
        await self._setup()
        await self.db.prepare(
            "insert into reports (tool, body, stamp) values (?, ?, ?) "
            "on conflict(tool) do update set body = excluded.body, stamp = excluded.stamp"
        ).bind(key, value, stamp).run()


_app = None


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi

        global _app
        if _app is None:
            key = getattr(self.env, "OPENROUTER_API_KEY", "") or ""
            _app = create_app(cache=D1Cache(self.env.DB), analyst_factory=lambda: LLMAnalyst(api_key=key))
        return await asgi.fetch(_app, request, self.env)
