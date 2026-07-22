from __future__ import annotations

from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_local_model: "SentenceTransformer | None" = None


def _get_local_model() -> "SentenceTransformer":
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _local_model


def embed(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "local":
        model = _get_local_model()
        return model.encode(text, normalize_embeddings=True).tolist()

    if settings.EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI()
        response = client.embeddings.create(input=text, model=settings.EMBEDDING_MODEL)
        return response.data[0].embedding

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{settings.EMBEDDING_PROVIDER}'. "
        "Expected 'local' or 'openai'."
    )
