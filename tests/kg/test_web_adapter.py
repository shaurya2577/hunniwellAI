import pytest

import kg.embeddings as embeddings
from kg.web_adapter import parse_memo
from kg.claims import query

SAMPLE_MEMO = """\
# Investment Memo: Acme Cardio

Acme Cardio is developing a transcatheter mitral valve repair device [INT-1].
The company reported FDA Breakthrough Device designation in Q1 2026 [EXT-1].
Equity raised to date is approximately $42M across two rounds [INT-1][EXT-1].

REFERENCES
[INT-1] acme_cardio_deck_2026.pdf
[EXT-1] FDA Grants Breakthrough Status — https://medtechdive.com/acme-cardio-breakthrough
"""

def _fake_embed(texts):
    out = []
    for t in texts:
        seed = sum(ord(c) for c in t)
        out.append([float((seed + i) % 7) for i in range(1024)])
    return out

def test_parse_memo_references_and_claims():
    parsed = parse_memo(SAMPLE_MEMO)

    refs = parsed["references"]
    assert set(refs.keys()) == {"INT-1", "EXT-1"}

    assert refs["INT-1"]["uri"] == "acme_cardio_deck_2026.pdf"
    assert refs["INT-1"]["title"] == "acme_cardio_deck_2026.pdf"
    assert refs["INT-1"]["kind"] in {"company_submitted", "internal_notes"}

    assert refs["EXT-1"]["uri"] == "https://medtechdive.com/acme-cardio-breakthrough"
    assert refs["EXT-1"]["title"] == "FDA Grants Breakthrough Status"
    assert refs["EXT-1"]["kind"] == "open_internet"

    claims = parsed["claims"]
    # one claim per sentence-with-citation in the body (3 cited statements)
    assert len(claims) == 3
    assert all(c["field"] is None for c in claims)

    by_tags = {tuple(sorted(c["tags"])): c["value"] for c in claims}
    assert ("INT-1",) in by_tags
    assert "transcatheter mitral valve" in by_tags[("INT-1",)]
    assert ("EXT-1",) in by_tags
    assert ("EXT-1", "INT-1") in by_tags  # sorted tags of the dual-cited statement


from kg.web_adapter import ingest_memo
from kg.companies import resolve_company

def test_ingest_memo_writes_sources_and_linked_claims(conn, monkeypatch):
    # Single module-attr patch covers write_claims' embed-on-write.
    monkeypatch.setattr("kg.embeddings.embed", _fake_embed)

    company_id = resolve_company(
        conn, "data/memos/acme.md", "Acme Cardio Inc.", "Q2-2026-review"
    )

    claim_ids = ingest_memo(conn, company_id, SAMPLE_MEMO, "data/memos/acme.md")
    assert len(claim_ids) == 3

    # one source per referenced tag, with correct kind + uri
    with conn.cursor() as cur:
        cur.execute(
            "select tag, kind, uri from sources where company_id = %s order by tag",
            (company_id,),
        )
        rows = cur.fetchall()
    src_by_tag = {r[0]: (r[1], r[2]) for r in rows}
    assert src_by_tag["INT-1"] == ("company_submitted", "acme_cardio_deck_2026.pdf")
    assert src_by_tag["EXT-1"] == (
        "open_internet",
        "https://medtechdive.com/acme-cardio-breakthrough",
    )

    # each claim is linked to the source of its primary (first, sorted) tag
    active = query(conn, company_id)
    assert len(active) == 3
    # statement cited only [INT-1] -> internal source uri
    mitral = next(c for c in active if "transcatheter mitral valve" in c.value)
    assert mitral.source_uri == "acme_cardio_deck_2026.pdf"
    assert mitral.source_kind == "company_submitted"
    # statement cited only [EXT-1] -> external source uri
    fda = next(c for c in active if "Breakthrough Device" in c.value)
    assert fda.source_uri == "https://medtechdive.com/acme-cardio-breakthrough"
    assert fda.source_kind == "open_internet"
