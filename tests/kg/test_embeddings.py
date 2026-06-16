import kg.embeddings as embeddings


class _FakeEmbedResult:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class _FakeVoyageClient:
    """Records calls and returns one 1024-float vector per input text."""

    def __init__(self, *args, **kwargs):
        self.calls = []

    def embed(self, texts, model=None, input_type=None):
        # Record the exact call so the test can assert batching/params.
        self.calls.append({"texts": list(texts), "model": model, "input_type": input_type})
        vectors = [[float(i)] * 1024 for i, _ in enumerate(texts)]
        return _FakeEmbedResult(vectors)


def _install_fake(monkeypatch):
    """Patch the voyageai.Client constructor and the cached module client so no
    network call is ever made. Also stub get_voyage_key so the tests need NO
    VOYAGE_API_KEY in the environment (the key is eval'd eagerly when the client
    is constructed, even though the fake constructor ignores it)."""
    fake = _FakeVoyageClient()
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "voyage")  # deterministic regardless of .env
    monkeypatch.setattr(embeddings, "get_voyage_key", lambda: "test-key")
    monkeypatch.setattr(embeddings.voyageai, "Client", lambda *a, **k: fake)
    # Reset any module-level cached client so the patched constructor is used.
    monkeypatch.setattr(embeddings, "_client", None, raising=False)
    return fake


def test_embed_returns_one_1024_vector_per_text(monkeypatch):
    _install_fake(monkeypatch)
    out = embeddings.embed(["a", "b"])
    assert len(out) == 2
    assert all(len(v) == 1024 for v in out)
    assert all(isinstance(x, float) for v in out for x in v)


def test_embed_batches_all_texts_in_one_call(monkeypatch):
    fake = _install_fake(monkeypatch)
    embeddings.embed(["a", "b", "c"])
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["texts"] == ["a", "b", "c"]
    assert call["model"] == "voyage-3.5"
    assert call["input_type"] == "document"


def test_embed_defaults_to_document_input_type(monkeypatch):
    fake = _install_fake(monkeypatch)
    embeddings.embed(["a"])
    assert fake.calls[0]["input_type"] == "document"


def test_embed_passes_through_query_input_type(monkeypatch):
    fake = _install_fake(monkeypatch)
    embeddings.embed(["a"], input_type="query")
    assert fake.calls[0]["input_type"] == "query"


def test_embed_empty_list_returns_empty_without_calling_client(monkeypatch):
    fake = _install_fake(monkeypatch)
    out = embeddings.embed([])
    assert out == []
    assert fake.calls == []


# ---- local Ollama backend (EMBEDDINGS_PROVIDER=ollama) -------------------------

class _FakeResp:
    def __init__(self, vec):
        self._vec = vec

    def raise_for_status(self):
        pass

    def json(self):
        return {"embedding": self._vec}


def _install_fake_ollama(monkeypatch, dim=1024):
    """Route embed() to the ollama backend and stub the HTTP call (no network)."""
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "ollama")
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json})
        return _FakeResp([0.1] * dim)

    monkeypatch.setattr(embeddings.requests, "post", fake_post)
    return calls


def test_embed_ollama_routes_and_returns_1024(monkeypatch):
    calls = _install_fake_ollama(monkeypatch)
    out = embeddings.embed(["a", "b"])
    assert len(out) == 2
    assert all(len(v) == 1024 for v in out)
    assert len(calls) == 2
    assert all(c["json"]["model"] == "mxbai-embed-large" for c in calls)
    assert calls[0]["json"]["prompt"] == "a"  # documents carry no query prefix


def test_embed_ollama_applies_query_prefix(monkeypatch):
    calls = _install_fake_ollama(monkeypatch)
    embeddings.embed(["seizure device"], input_type="query")
    assert calls[0]["json"]["prompt"].startswith(
        "Represent this sentence for searching relevant passages: "
    )
    assert calls[0]["json"]["prompt"].endswith("seizure device")


def test_embed_ollama_rejects_wrong_dim(monkeypatch):
    _install_fake_ollama(monkeypatch, dim=768)
    try:
        embeddings.embed(["a"])
        assert False, "expected ValueError on dim mismatch"
    except ValueError as e:
        assert "768" in str(e) and "1024" in str(e)
