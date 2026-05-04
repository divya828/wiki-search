import asyncio
from threading import Lock

from sentence_transformers import SentenceTransformer

from app.config import get_settings

_model: SentenceTransformer | None = None
_lock = Lock()


def _load_model() -> SentenceTransformer:
    global _model
    with _lock:
        if _model is None:
            _model = SentenceTransformer(get_settings().embedding_model)
        return _model


def embed_sync(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


async def embed(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(embed_sync, texts)


def warm() -> None:
    """Load model into memory (call at startup so first request is fast)."""
    _load_model()
