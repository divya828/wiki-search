from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.retriever import RetrievedChunk

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = (
    "You are a careful Wikipedia research assistant. Answer the user's question "
    "using only the provided Wikipedia excerpts. Cite the article title in square "
    "brackets after each claim, like [Marie Curie]. If the excerpts do not contain "
    "the answer, say 'The provided sources don't contain the answer to that question.' "
    "Keep answers concise: 2-5 sentences unless the question demands more."
)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    return _client


async def close_anthropic_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def _build_user_message(question: str, chunks: list[RetrievedChunk]) -> str:
    lines = ["Question:", question, "", "Wikipedia excerpts:"]
    for i, c in enumerate(chunks, start=1):
        section = f" — section: {c.section}" if c.section else ""
        lines.append(f"\n[{i}] [source: {c.article_title}{section}]")
        lines.append(c.chunk_text)
    return "\n".join(lines)


async def stream_answer(question: str, chunks: list[RetrievedChunk]) -> AsyncIterator[str]:
    user_msg = _build_user_message(question, chunks)
    async with _get_client().messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
