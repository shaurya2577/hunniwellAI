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
    network call is ever made."""
    fake = _FakeVoyageClient()
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


def test_embed_empty_list_returns_empty_without_calling_client(monkeypatch):
    fake = _install_fake(monkeypatch)
    out = embeddings.embed([])
    assert out == []
    assert fake.calls == []
