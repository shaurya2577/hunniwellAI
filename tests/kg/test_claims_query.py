import pytest

from kg.companies import resolve_company
from kg.sources import upsert_source
from kg.claims import write_claims, query
from kg.models import Claim, ClaimInput

@pytest.fixture(autouse=True)
def _fake_embed(monkeypatch):
    """Deterministic 1024-float embedding derived from the text; never hits the
    network. One patch on the module attr `kg.embeddings.embed` covers every
    caller (write_claims reaches it via `embeddings.embed`)."""
    def fake_embed(texts):
        out = []
        for t in texts:
            seed = sum(ord(c) for c in t)
            out.append([float((seed + i) % 97) / 97.0 for i in range(1024)])
        return out
    monkeypatch.setattr("kg.embeddings.embed", fake_embed)
    return fake_embed

def test_query_returns_claims_with_joined_source_fields(conn):
    company_id = resolve_company(conn, "events/demo/acme.md", "Acme Inc", "demo")
    source_id = upsert_source(
        conn,
        company_id,
        kind="third_party",
        uri="https://example.com/report",
        writer="alice",
    )
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [
            ClaimInput(field="short_description", value="Implantable glucose sensor."),
            ClaimInput(field="medical_field", value="Endocrinology"),
        ],
        writer="alice",
    )
    assert len(ids) == 2

    rows = query(conn, company_id)
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert all(isinstance(r, Claim) for r in rows)

    by_field = {r.field: r for r in rows}
    desc = by_field["short_description"]
    assert desc.value == "Implantable glucose sensor."
    assert desc.company_id == company_id
    assert desc.source_id == source_id
    assert desc.status == "active"
    # joined from sources
    assert desc.reliability == 4  # DEFAULT_RELIABILITY['third_party']
    assert desc.source_uri == "https://example.com/report"
    assert desc.source_kind == "third_party"

def test_query_filters_by_fields(conn):
    company_id = resolve_company(conn, "events/demo/acme.md", "Acme Inc", "demo")
    source_id = upsert_source(conn, company_id, kind="third_party", uri=None, writer="alice")
    write_claims(
        conn,
        company_id,
        source_id,
        [
            ClaimInput(field="short_description", value="Implantable glucose sensor."),
            ClaimInput(field="medical_field", value="Endocrinology"),
        ],
        writer="alice",
    )

    rows = query(conn, company_id, fields=["short_description"])
    assert len(rows) == 1
    assert rows[0].field == "short_description"
    assert rows[0].value == "Implantable glucose sensor."

def test_query_only_returns_active_status(conn):
    company_id = resolve_company(conn, "events/demo/acme.md", "Acme Inc", "demo")
    source_id = upsert_source(conn, company_id, kind="third_party", uri=None, writer="alice")
    ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="status_field", value="Series A")],
        writer="alice",
    )
    # Manually retire the claim; query must exclude non-active rows.
    with conn.cursor() as cur:
        cur.execute("update claims set status='superseded' where id = %s", (ids[0],))
    conn.commit()

    rows = query(conn, company_id)
    assert rows == []

def test_query_empty_company_returns_empty_list(conn):
    company_id = resolve_company(conn, "events/demo/acme.md", "Acme Inc", "demo")
    rows = query(conn, company_id)
    assert rows == []
