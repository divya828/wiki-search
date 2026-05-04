from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.chunker import chunk_article
from app.db import close_pool, init_pool
from app.embedder import embed, warm as warm_embedder
from app.indexer import index_article, is_indexed
from app.router import classify
from app.wiki_client import close_wiki_client, get_wiki_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_pool()
    get_wiki_client()
    warm_embedder()
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


@app.get("/api/_debug/route")
async def debug_route(q: str):
    result = await classify(q, get_wiki_client())
    return {"kind": result.kind, "resolved_title": result.resolved_title}


@app.get("/api/_debug/chunks/{title}")
async def debug_chunks(title: str):
    html = await get_wiki_client().get_full_article(title)
    if html is None:
        return {"error": "not found"}
    chunks = chunk_article(html)
    return {
        "count": len(chunks),
        "first": (
            {"section": chunks[0].section, "text": chunks[0].text[:300]}
            if chunks else None
        ),
        "sections": list({c.section for c in chunks}),
    }


@app.post("/api/_debug/embed")
async def debug_embed(body: dict):
    text: str = body["text"]
    vectors = await embed([text])
    return {"dim": len(vectors[0]), "first5": vectors[0][:5]}


@app.post("/api/_debug/index/{title}")
async def debug_index(title: str):
    canonical = title.replace("_", " ")
    inserted = await index_article(canonical, get_wiki_client())
    return {"inserted": inserted, "indexed": await is_indexed(canonical)}
