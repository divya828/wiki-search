from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

# Approximate words-per-chunk to stay around 500 tokens (~1.3 tokens/word)
TARGET_WORDS = 380
OVERLAP_WORDS = 40

# Selectors to strip before parsing paragraphs
DROP_SELECTORS = [
    "table.infobox",
    ".navbox",
    ".reflist",
    ".references",
    "ol.references",
    "div.thumb",
    "sup.reference",
    "span.mw-editsection",
    "table.metadata",
    "div.hatnote",
    ".sidebar",
]


@dataclass
class Chunk:
    section: str
    text: str


def _strip(soup: BeautifulSoup) -> None:
    for sel in DROP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()


def _walk_sections(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    Walk the article body. Return [(section_title, paragraph_text), ...].
    Section title carries the most recent h2/h3 heading (defaults to "Introduction").
    """
    out: list[tuple[str, str]] = []
    current_section = "Introduction"
    body = soup.find("body") or soup
    for el in body.find_all(["h2", "h3", "h4", "p"]):
        if not isinstance(el, Tag):
            continue
        if el.name in {"h2", "h3", "h4"}:
            heading = el.get_text(" ", strip=True)
            if heading:
                current_section = heading
        else:
            text = el.get_text(" ", strip=True)
            if text:
                out.append((current_section, text))
    return out


def _pack_chunks(paragraphs: list[tuple[str, str]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    buf_section: str | None = None
    buf_words: list[str] = []

    def flush() -> None:
        nonlocal buf_words, buf_section
        if buf_words and buf_section is not None:
            chunks.append(Chunk(section=buf_section, text=" ".join(buf_words)))
        buf_words = []
        buf_section = None

    for section, text in paragraphs:
        words = text.split()
        if buf_section is None:
            buf_section = section
        # If the section changes mid-buffer, flush first.
        if section != buf_section:
            flush()
            buf_section = section
        for w in words:
            buf_words.append(w)
            if len(buf_words) >= TARGET_WORDS:
                # Emit chunk and keep an overlap tail.
                chunks.append(Chunk(section=buf_section, text=" ".join(buf_words)))
                buf_words = buf_words[-OVERLAP_WORDS:] if OVERLAP_WORDS else []
    flush()
    return chunks


def chunk_article(html: str) -> list[Chunk]:
    soup = BeautifulSoup(html, "lxml")
    _strip(soup)
    paragraphs = _walk_sections(soup)
    return _pack_chunks(paragraphs)
