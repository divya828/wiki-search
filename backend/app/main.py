from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import close_pool, init_pool
from app.wiki_client import close_wiki_client, get_wiki_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_pool()
    get_wiki_client()
    try:
        yield
    finally:
        try:
            await close_wiki_client()
        finally:
            await close_pool()


app = FastAPI(title="Wiki Search", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/_debug/summary/{title}")
async def debug_summary(title: str):
    return await get_wiki_client().get_summary(title)


@app.get("/api/_debug/search")
async def debug_search(q: str):
    return await get_wiki_client().search_articles(q, limit=5)
