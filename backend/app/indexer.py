from app.chunker import chunk_article
from app.db import get_pool
from app.embedder import embed
from app.wiki_client import WikiClient


async def is_indexed(article_title: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select 1 from chunks where article_title = $1 limit 1",
            article_title,
        )
        return row is not None


async def index_article(article_title: str, client: WikiClient) -> int:
    """Fetch + chunk + embed + insert. Returns number of chunks inserted."""
    if await is_indexed(article_title):
        return 0
    html = await client.get_full_article(article_title)
    if html is None:
        raise ValueError(f"article not found: {article_title}")
    chunks = chunk_article(html)
    if not chunks:
        return 0
    texts = [f"# {c.section}\n{c.text}" for c in chunks]
    vectors = await embed(texts)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                insert into chunks (article_title, section, chunk_text, embedding)
                values ($1, $2, $3, $4)
                """,
                [
                    (article_title, c.section, c.text, v)
                    for c, v in zip(chunks, vectors)
                ],
            )
    return len(chunks)
