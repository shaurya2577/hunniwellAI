"""Embedding wrapper. Default backend Voyage (voyage-3.5, dim 1024); set
EMBEDDINGS_PROVIDER=ollama for a local 1024-dim backend (mxbai-embed-large).

SOLE author of this module. Callers import it as a module (`from kg import
embeddings`) and call `embeddings.embed(...)`, so tests patch `kg.embeddings.embed`
(or a backend's internals) to avoid the network. Empty input short-circuits before
any backend work. Both backends emit length-1024 vectors so the schema's
vector(1024) column is provider-agnostic.
"""
from __future__ import annotations

import requests
import voyageai

from kg.config import (
    get_embeddings_provider,
    get_ollama_embed_model,
    get_ollama_url,
    get_voyage_key,
)

MODEL = "voyage-3.5"
DIM = 1024
# mxbai-embed-large asks that *queries* (not stored documents) carry this prefix.
_MXBAI_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=get_voyage_key())
    return _client


def _embed_voyage(texts: list[str], input_type: str) -> list[list[float]]:
    result = _get_client().embed(texts, model=MODEL, input_type=input_type)
    return [[float(x) for x in vec] for vec in result.embeddings]


def _embed_ollama(texts: list[str], input_type: str) -> list[list[float]]:
    url = get_ollama_url().rstrip("/") + "/api/embeddings"
    model = get_ollama_embed_model()
    out: list[list[float]] = []
    for t in texts:
        prompt = (_MXBAI_QUERY_PREFIX + t) if input_type == "query" else t
        resp = requests.post(url, json={"model": model, "prompt": prompt}, timeout=60)
        resp.raise_for_status()
        vec = resp.json().get("embedding", [])
        if len(vec) != DIM:
            raise ValueError(
                f"Ollama model {model!r} returned dim {len(vec)}, expected {DIM}. "
                f"Use a {DIM}-dim model (e.g. mxbai-embed-large) or change the schema dim."
            )
        out.append([float(x) for x in vec])
    return out


def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed texts; each vector has length 1024.

    input_type: "document" (default) for stored claims, "query" for search queries.
    Backend chosen by EMBEDDINGS_PROVIDER: "voyage" (default) or "ollama" (local).
    Returns [] immediately for empty input (no backend call, no network).
    """
    if not texts:
        return []
    if get_embeddings_provider() == "ollama":
        return _embed_ollama(texts, input_type)
    return _embed_voyage(texts, input_type)
