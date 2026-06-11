import re

import pytest

import kg.embeddings
from kg.claims import write_claims
from kg.companies import resolve_company
from kg.models import ClaimInput
from kg.sources import upsert_source

CLAIM_ID_RE = re.compile(r"^clm_[0-9a-f]{32}$")


def _fake_vec(text: str) -> list[float]:
    # Deterministic 1024-float vector seeded by the text; no network.
    seed = sum(ord(c) for c in text) or 1
    return [((seed * (i + 1)) % 997) / 997.0 for i in range(1024)]


@pytest.fixture
def patched_embed(monkeypatch):
    calls = {"n": 0}

    def fake_embed(texts):
        calls["n"] += 1
        assert isinstance(texts, list)
        return [_fake_vec(t) for t in texts]

    # Single patch on the module attr covers every caller (claims.py uses
    # `from kg import embeddings; embeddings.embed(...)`).
    monkeypatch.setattr("kg.embeddings.embed", fake_embed)
    return calls


@pytest.fixture
def company_and_source(conn):
    company_id = resolve_company(conn, "events/x/co.md", "Acme Inc", "x")
    source_id = upsert_source(
        conn, company_id, "company_submitted", None, writer="ingest"
    )
    return company_id, source_id


def test_write_claims_returns_claim_ids(conn, patched_embed, company_and_source):
    company_id, source_id = company_and_source
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston"), ClaimInput(field="stage", value="Seed")],
        writer="ingest",
    )
    assert len(ids) == 2
    for cid in ids:
        assert CLAIM_ID_RE.match(cid), cid
    assert len(set(ids)) == 2


def test_write_claims_persists_embedding_dim_1024(conn, patched_embed, company_and_source):
    company_id, source_id = company_and_source
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston")],
        writer="ingest",
    )
    with conn.cursor() as cur:
        cur.execute("select embedding from claims where id = %s", (ids[0],))
        (embedding,) = cur.fetchone()
    assert embedding is not None
    assert len(list(embedding)) == 1024


def test_write_claims_idempotent_same_field_value_source(conn, patched_embed, company_and_source):
    company_id, source_id = company_and_source
    first = write_claims(
        conn, company_id, source_id, [ClaimInput(field="hq", value="Boston")], writer="ingest"
    )
    second = write_claims(
        conn, company_id, source_id, [ClaimInput(field="hq", value="Boston")], writer="ingest"
    )
    assert first == second
    with conn.cursor() as cur:
        cur.execute(
            "select count(*) from claims where company_id = %s and field = %s and status = 'active'",
            (company_id, "hq"),
        )
        (n,) = cur.fetchone()
    assert n == 1


def test_write_claims_two_values_same_field_coexist(conn, patched_embed, company_and_source):
    company_id, source_id = company_and_source
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston"), ClaimInput(field="hq", value="Cambridge")],
        writer="ingest",
    )
    assert len(set(ids)) == 2
    with conn.cursor() as cur:
        cur.execute(
            "select count(*) from claims where company_id = %s and field = %s and status = 'active'",
            (company_id, "hq"),
        )
        (n,) = cur.fetchone()
    assert n == 2


def test_write_claims_field_none_allowed(conn, patched_embed, company_and_source):
    company_id, source_id = company_and_source
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field=None, value="raw memo line")],
        writer="ingest",
    )
    assert len(ids) == 1 and CLAIM_ID_RE.match(ids[0])
    with conn.cursor() as cur:
        cur.execute("select field, value from claims where id = %s", (ids[0],))
        field, value = cur.fetchone()
    assert field is None and value == "raw memo line"
