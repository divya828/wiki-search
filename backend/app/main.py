import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.answer import close_anthropic_client, stream_answer
from app.db import close_pool, init_pool
from app.embedder import warm as warm_embedder
from app.indexer import index_article, is_indexed
from app.jobs import (
    Job,
    close as close_job,
    create_job,
    get_job,
    push_error,
    push_status,
    push_token,
    run_websocket,
)
from app.retriever import retrieve
from app.router import classify
from app.wiki_client import close_wiki_client, get_wiki_client


# In-process locks per article title — coalesces concurrent indexing requests
# for the same article so we don't double-fetch / double-insert.
_index_locks: dict[str, asyncio.Lock] = {}


def _index_lock(article_title: str) -> asyncio.Lock:
    lock = _index_locks.get(article_title)
    if lock is None:
        lock = asyncio.Lock()
        _index_locks[article_title] = lock
    return lock


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_pool()
    get_wiki_client()
    warm_embedder()
    try:
        yield
    finally:
        try:
            await close_anthropic_client()
        finally:
            try:
                await close_wiki_client()
            finally:
                await close_pool()


app = FastAPI(title="Wiki Search", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query: str
    mode: Literal["ask", "search"] = "ask"


@app.post("/api/search")
async def search(req: SearchRequest, background: BackgroundTasks) -> dict:
    client = get_wiki_client()

    if req.mode == "search":
        hits = await client.search_articles(req.query, limit=10)
        return {
            "fallback": {"type": "search_results", "hits": hits},
            "job_id": None,
        }

    # Ask mode
    route = await classify(req.query, client)

    if route.kind == "broad":
        hits = await client.search_articles(req.query, limit=10)
        return {
            "fallback": {"type": "search_results", "hits": hits},
            "job_id": None,
        }

    title = route.resolved_title
    assert title is not None
    summary = await client.get_summary(title)
    if summary is None or summary["type"] == "missing":
        return {
            "fallback": {"type": "no_results", "message": "No Wikipedia article found"},
            "job_id": None,
        }

    job = create_job(query=req.query, article_title=title)
    background.add_task(_run_ask_job, job)

    return {
        "fallback": {
            "type": "summary",
            "title": summary["title"],
            "extract": summary["extract"],
            "thumbnail": summary["thumbnail"],
        },
        "job_id": job.id,
    }


async def _run_ask_job(job: Job) -> None:
    client = get_wiki_client()
    title = job.article_title
    assert title is not None
    try:
        # Coalesce concurrent indexing for the same title
        async with _index_lock(title):
            if not await is_indexed(title):
                await push_status(job, "indexing", article=title)
                await index_article(title, client)
        await push_status(job, "indexed", article=title)

        await push_status(job, "answering")
        chunks = await retrieve(job.query)
        sources = sorted({c.article_title for c in chunks})
        async for text in stream_answer(job.query, chunks):
            await push_token(job, text)
        await push_status(job, "done", sources=sources)
    except Exception as e:  # noqa: BLE001
        await push_error(job, str(e))
    finally:
        await close_job(job)


@app.websocket("/api/jobs/{job_id}/stream")
async def jobs_stream(websocket: WebSocket, job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "job not found"})
        await websocket.close()
        return
    try:
        await run_websocket(job, websocket)
    except WebSocketDisconnect:
        # Client closed first; producer will keep running so cache fills.
        return
