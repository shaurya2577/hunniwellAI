import hashlib

import pytest

from kg.companies import resolve_company
from kg.sources import upsert_source
from kg.claims import write_claims
from kg.models import ClaimInput
from kg.search import semantic_search

def _basis_vec(index: int) -> list[float]:
    """Unit vector pointing along axis `index` in 1024-dim space."""
    v = [0.0] * 1024
    v[index] = 1.0
    return v

# Map known claim texts to known basis vectors so cosine ordering is exact.
TEXT_TO_AXIS = {
    "cardiac ablation catheter": 0,
    "spinal fusion implant": 1,
    "glucose monitoring wearable": 2,
}

def _fake_embed(texts, input_type="document"):
    out = []
    for t in texts:
        if t in TEXT_TO_AXIS:
            out.append(_basis_vec(TEXT_TO_AXIS[t]))
        else:
            # Deterministic fallback: a single hot axis derived from the text hash.
            h = int(hashlib.sha256(t.encode()).hexdigest(), 16)
            out.append(_basis_vec(h % 1024))
    return out

@pytest.fixture(autouse=True)
def _patch_embed(monkeypatch):
    # Single module-attr patch covers BOTH write_claims (embed-on-write) and
    # semantic_search (embed-the-query); both call `embeddings.embed(...)`.
    monkeypatch.setattr("kg.embeddings.embed", _fake_embed)

def _seed_company(conn, relpath, name, event="Test Event"):
    company_id = resolve_company(conn, relpath, name, event)
    source_id = upsert_source(
        conn, company_id, "company_submitted", None, writer="tester"
    )
    return company_id, source_id

def test_nearest_claim_returned_first(conn):
    company_id, source_id = _seed_company(conn, "memos/a.md", "Acme Inc")
    write_claims(
        conn,
        company_id,
        source_id,
        [
            ClaimInput(field="device", value="cardiac ablation catheter"),
            ClaimInput(field="device", value="spinal fusion implant"),
            ClaimInput(field="device", value="glucose monitoring wearable"),
        ],
        writer="tester",
    )

    results = semantic_search(conn, "spinal fusion implant", k=3)

    assert len(results) == 3
    assert results[0].value == "spinal fusion implant"

def test_k_limits_results(conn):
    company_id, source_id = _seed_company(conn, "memos/b.md", "Beta LLC")
    write_claims(
        conn,
        company_id,
        source_id,
        [
            ClaimInput(field="device", value="cardiac ablation catheter"),
            ClaimInput(field="device", value="spinal fusion implant"),
            ClaimInput(field="device", value="glucose monitoring wearable"),
        ],
        writer="tester",
    )

    results = semantic_search(conn, "cardiac ablation catheter", k=1)

    assert len(results) == 1
    assert results[0].value == "cardiac ablation catheter"

def test_company_id_filters_scope(conn):
    a_id, a_src = _seed_company(conn, "memos/c.md", "Acme Inc")
    b_id, b_src = _seed_company(conn, "memos/d.md", "Beta LLC")
    write_claims(
        conn,
        a_id,
        a_src,
        [ClaimInput(field="device", value="cardiac ablation catheter")],
        writer="tester",
    )
    write_claims(
        conn,
        b_id,
        b_src,
        [ClaimInput(field="device", value="cardiac ablation catheter")],
        writer="tester",
    )

    results = semantic_search(
        conn, "cardiac ablation catheter", k=10, company_id=b_id
    )

    assert len(results) == 1
    assert results[0].company_id == b_id
    assert results[0].value == "cardiac ablation catheter"

def test_semantic_search_embeds_query_with_query_input_type(conn, monkeypatch):
    # The query embedding must use input_type="query"; document writes use
    # input_type="document".
    captured = {}

    def capturing_embed(texts, input_type="document"):
        captured["input_type"] = input_type
        return _fake_embed(texts)

    monkeypatch.setattr("kg.embeddings.embed", capturing_embed)
    company_id, source_id = _seed_company(conn, "memos/q.md", "Query Co")
    semantic_search(conn, "cardiac ablation catheter", k=1)
    assert captured["input_type"] == "query"


def test_write_claims_embeds_with_document_input_type(conn, monkeypatch):
    captured = []

    def capturing_embed(texts, input_type="document"):
        captured.append(input_type)
        return _fake_embed(texts)

    monkeypatch.setattr("kg.embeddings.embed", capturing_embed)
    company_id, source_id = _seed_company(conn, "memos/w.md", "Write Co")
    write_claims(
        conn, company_id, source_id,
        [ClaimInput(field="device", value="cardiac ablation catheter")],
        writer="tester",
    )
    assert captured == ["document"]


def test_returns_claim_with_source_join_fields(conn):
    company_id, source_id = _seed_company(conn, "memos/e.md", "Gamma Corp")
    write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="device", value="glucose monitoring wearable")],
        writer="tester",
    )

    results = semantic_search(conn, "glucose monitoring wearable", k=5)

    assert results[0].source_kind == "company_submitted"
    assert results[0].reliability == 3  # DEFAULT_RELIABILITY['company_submitted']
    assert results[0].status == "active"
