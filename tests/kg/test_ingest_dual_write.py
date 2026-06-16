import importlib

import pytest

def _fake_embed(texts):
    # deterministic 1024-float vector seeded off the text length/content; no network
    return [[float((len(t) + i) % 7) for i in range(1024)] for t in texts]

def test_kg_dual_write_creates_company_source_and_claims(conn, monkeypatch):
    # Single module-attr patch covers write_claims' embed-on-write.
    monkeypatch.setattr("kg.embeddings.embed", _fake_embed)

    from ai.airtable_ingest import ingest

    record = {
        "company": "Auvi Labs Inc.",
        "event": "JPM 2026 (260115)",
        "data_entry": "AI",
        "country": "United States",
        "medical_field": "Nephrology",
        "short_description": "Implantable dialysis device.",
    }
    relpath = "JPM 2026 (260115)/Auvi Labs"

    ingest.kg_dual_write(conn, record, relpath)

    with conn.cursor() as cur:
        # company created once, deduped on name_norm
        cur.execute("select id, name_norm, name_raw from companies")
        rows = cur.fetchall()
        assert len(rows) == 1
        company_id, name_norm, name_raw = rows[0]
        assert name_norm == "auvilabs"
        assert name_raw == "Auvi Labs Inc."

        # company_appearances row for relpath (== state_key)
        cur.execute("select event, relpath from company_appearances where company_id = %s", (company_id,))
        appearances = cur.fetchall()
        assert appearances == [("JPM 2026 (260115)", relpath)]

        # exactly one company_submitted source written by 'ingest'
        cur.execute("select kind, writer, reliability, uri from sources where company_id = %s", (company_id,))
        srows = cur.fetchall()
        assert len(srows) == 1
        kind, writer, reliability, uri = srows[0]
        assert kind == "company_submitted"
        assert writer == "ingest"
        assert reliability == 3  # DEFAULT_RELIABILITY['company_submitted']
        assert uri is None

        # one active claim per FIELD_MAP json_key present, excluding company/event/data_entry
        cur.execute("select field, value, status, writer from claims where company_id = %s order by field", (company_id,))
        crows = cur.fetchall()
        fields = sorted(r[0] for r in crows)
        assert fields == ["country", "medical_field", "short_description"]
        assert all(r[2] == "active" for r in crows)
        assert all(r[3] == "ingest" for r in crows)
        cvals = {r[0]: r[1] for r in crows}
        assert cvals["country"] == "United States"
        assert cvals["medical_field"] == "Nephrology"

def test_kg_disabled_never_calls_connect(monkeypatch):
    # When SUPABASE_DB_URL is unset and --kg not passed, _maybe_kg_conn must
    # return None WITHOUT attempting any connect() (so ingest runs fully without KG).
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    from ai.airtable_ingest import ingest
    importlib.reload(ingest)

    def _boom(*a, **k):
        raise AssertionError(
            "connect() must not be called when SUPABASE_DB_URL is unset and --kg not passed"
        )

    # Patch the symbol ingest.py actually calls.
    monkeypatch.setattr(ingest, "connect", _boom, raising=False)

    # Must return None and must NOT raise (i.e. connect was never invoked).
    assert ingest._maybe_kg_conn(use_kg_flag=False) is None
