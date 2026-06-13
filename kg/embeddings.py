"""Voyage embedding wrapper. Model voyage-3.5, dim 1024.

SOLE author of this module (Task 6). Callers import it as a module
(`from kg import embeddings`) and call `embeddings.embed(...)`, so tests patch
`kg.embeddings.embed` (or `kg.embeddings.voyageai.Client`) to avoid the network.
The module-level `_client` is cached and empty-list inputs short-circuit before
any client construction.
"""
from __future__ import annotations

import voyageai

from kg.config import get_voyage_key

MODEL = "voyage-3.5"
DIM = 1024

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=get_voyage_key())
    return _client


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed texts in a single batched Voyage call. Each vector has length 1024.

    input_type is passed through to Voyage: use "document" for claims/documents
    being stored (the default) and "query" for search queries.

    Returns [] immediately for empty input (no client construction, no network).
    """
    if not texts:
        return []
    result = _get_client().embed(texts, model=MODEL, input_type=input_type)
    return [[float(x) for x in vec] for vec in result.embeddings]
