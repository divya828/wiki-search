from dataclasses import dataclass

import asyncpg

from app.db import get_pool
from app.embedder import embed

VECTOR_K = 20
KEYWORD_K = 20
RRF_K = 60
TOP_N = 5


@dataclass
class RetrievedChunk:
    article_title: str
    section: str | None
    chunk_text: str
    score: float


async def retrieve(query: str) -> list[RetrievedChunk]:
    [query_vec] = await embed([query])
    pool = get_pool()
    async with pool.acquire() as conn:
        vector_rows = await conn.fetch(
            """
            select id, article_title, section, chunk_text
            from chunks
            order by embedding <=> $1
            limit $2
            """,
            query_vec,
            VECTOR_K,
        )
        keyword_rows = await conn.fetch(
            """
            select id, article_title, section, chunk_text
            from chunks
            where tsv @@ plainto_tsquery('english', $1)
            order by ts_rank(tsv, plainto_tsquery('english', $1)) desc
            limit $2
            """,
            query,
            KEYWORD_K,
        )

    scores: dict[int, float] = {}
    payloads: dict[int, asyncpg.Record] = {}

    for rank, row in enumerate(vector_rows):
        scores[row["id"]] = scores.get(row["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        payloads[row["id"]] = row
    for rank, row in enumerate(keyword_rows):
        scores[row["id"]] = scores.get(row["id"], 0.0) + 1.0 / (RRF_K + rank + 1)
        payloads.setdefault(row["id"], row)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    return [
        RetrievedChunk(
            article_title=payloads[cid]["article_title"],
            section=payloads[cid]["section"],
            chunk_text=payloads[cid]["chunk_text"],
            score=score,
        )
        for cid, score in ranked
    ]
