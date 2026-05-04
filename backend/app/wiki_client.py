from typing import Literal, TypedDict
from urllib.parse import quote

import httpx

REST_BASE = "https://en.wikipedia.org/api/rest_v1"
ACTION_BASE = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "wiki-search/0.1 (https://github.com/yourname/wiki-search)"


class Summary(TypedDict):
    title: str
    extract: str
    thumbnail: str | None
    type: Literal["standard", "disambiguation", "no-extract", "missing"]


class SearchHit(TypedDict):
    title: str
    snippet: str


class WikiClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_summary(self, title: str) -> Summary | None:
        url = f"{REST_BASE}/page/summary/{quote(title, safe='')}"
        r = await self._client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        thumb = data.get("thumbnail", {}).get("source") if data.get("thumbnail") else None
        return Summary(
            title=data["title"],
            extract=data.get("extract", ""),
            thumbnail=thumb,
            type=data.get("type", "standard"),
        )

    async def search_articles(self, query: str, limit: int = 10) -> list[SearchHit]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(limit),
            "format": "json",
            "formatversion": "2",
        }
        r = await self._client.get(ACTION_BASE, params=params)
        r.raise_for_status()
        results = r.json().get("query", {}).get("search", [])
        return [
            SearchHit(title=item["title"], snippet=item.get("snippet", ""))
            for item in results
        ]

    async def get_full_article(self, title: str) -> str | None:
        url = f"{REST_BASE}/page/html/{quote(title, safe='')}"
        r = await self._client.get(url)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text


_client: WikiClient | None = None


def get_wiki_client() -> WikiClient:
    global _client
    if _client is None:
        _client = WikiClient()
    return _client


async def close_wiki_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
