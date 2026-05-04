from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from app.wiki_client import WikiClient

SIMILARITY_THRESHOLD = 0.8


@dataclass
class RouteResult:
    kind: Literal["single_topic", "broad"]
    resolved_title: str | None  # the canonical Wikipedia title (single_topic only)


def _normalize(s: str) -> str:
    return s.lower().strip().replace("_", " ")


async def classify(query: str, client: WikiClient) -> RouteResult:
    hits = await client.search_articles(query, limit=1)
    if not hits:
        return RouteResult(kind="broad", resolved_title=None)
    top_title = hits[0]["title"]
    similarity = SequenceMatcher(None, _normalize(query), _normalize(top_title)).ratio()
    if similarity >= SIMILARITY_THRESHOLD:
        return RouteResult(kind="single_topic", resolved_title=top_title)
    return RouteResult(kind="broad", resolved_title=None)
