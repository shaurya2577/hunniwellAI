import uuid

import pytest

from kg.citations import CITATION_RE, resolve_citation, validate_citations
from kg.companies import resolve_company
from kg.sources import upsert_source
from kg.claims import write_claims
from kg.models import ClaimInput


def _fake_embed(texts):
    out = []
    for t in texts:
        seed = sum(ord(c) for c in t) or 1
        out.append([((seed * (i + 1)) % 1000) / 1000.0 for i in range(1024)])
    return out


@pytest.fixture(autouse=True)
def _patch_embed(monkeypatch):
    # Single module-attr patch; write_claims reaches embed via embeddings.embed.
    monkeypatch.setattr("kg.embeddings.embed", _fake_embed)


def _make_claim(conn, value="Series A raised $5M", field="funding"):
    cid = resolve_company(conn, "events/x/co.pdf", "Acme Inc", "X-2026")
    sid = upsert_source(conn, cid, "company_submitted", None, writer="t")
    [claim_id] = write_claims(conn, cid, sid, [ClaimInput(field=field, value=value)], writer="t")
    return cid, claim_id, value


def test_citation_re_extracts_token():
    text = "Funding is solid [[clm_" + "a" * 32 + "]] per the deck."
    assert CITATION_RE.findall(text) == ["clm_" + "a" * 32]


def test_resolve_citation_returns_claim_fields(conn):
    cid, claim_id, value = _make_claim(conn)
    rec = resolve_citation(conn, claim_id)
    assert rec["claim_id"] == claim_id
    assert rec["value"] == value
    assert rec["source_kind"] == "company_submitted"
    assert rec["reliability"] == 3  # DEFAULT_RELIABILITY['company_submitted']
    assert rec["source_uri"] is None
    assert set(rec.keys()) == {"claim_id", "value", "source_uri", "source_kind", "reliability"}


def test_resolve_citation_unknown_raises_keyerror(conn):
    unknown = "clm_" + uuid.uuid4().hex
    with pytest.raises(KeyError):
        resolve_citation(conn, unknown)


def test_validate_citations_flags_unknown_token(conn):
    cid, claim_id, _ = _make_claim(conn)
    unknown = "clm_" + uuid.uuid4().hex
    text = f"Good [[{claim_id}]] but bad [[{unknown}]]."
    assert validate_citations(conn, text, cid) == [unknown]


def test_validate_citations_ignores_non_token_text(conn):
    cid, claim_id, _ = _make_claim(conn)
    text = "No citations here, just prose about clm_ and [[notaclaim]]."
    assert validate_citations(conn, text, cid) == []


def test_validate_citations_multiple_tokens_all_valid(conn):
    cid = resolve_company(conn, "events/x/co.pdf", "Acme Inc", "X-2026")
    sid = upsert_source(conn, cid, "company_submitted", None, writer="t")
    ids = write_claims(
        conn,
        cid,
        sid,
        [ClaimInput(field="a", value="one"), ClaimInput(field="b", value="two")],
        writer="t",
    )
    text = f"[[{ids[0]}]] and again [[{ids[0]}]] plus [[{ids[1]}]]"
    assert validate_citations(conn, text, cid) == []


def test_validate_citations_wrong_company_is_unresolved(conn):
    cid_a, claim_id, _ = _make_claim(conn)
    cid_b = resolve_company(conn, "events/y/other.pdf", "Beta LLC", "Y-2026")
    text = f"Claim [[{claim_id}]] belongs elsewhere."
    assert validate_citations(conn, text, cid_b) == [claim_id]
