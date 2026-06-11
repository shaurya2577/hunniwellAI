import time

import pytest

import kg.embeddings
from kg.companies import resolve_company
from kg.sources import upsert_source
from kg.claims import write_claims
from kg.export import to_airtable_record
from kg.models import ClaimInput
from ai.airtable_ingest.ingest import FIELD_MAP


@pytest.fixture(autouse=True)
def _fake_embed(monkeypatch):
    # Deterministic 1024-float vector derived from text; never hits the network.
    def fake_embed(texts):
        out = []
        for t in texts:
            seed = sum(ord(c) for c in t)
            out.append([float((seed + i) % 97) / 97.0 for i in range(1024)])
        return out

    monkeypatch.setattr(kg.embeddings, "embed", fake_embed)
    return fake_embed


def test_higher_reliability_wins_same_field(conn):
    company_id = resolve_company(conn, "JPM/Acme/deck.pdf", "Acme Inc", "JPM 2026")
    # third_party reliability=4
    src_hi = upsert_source(
        conn, company_id, kind="third_party", uri="https://hi.example",
        writer="alice",
    )
    # open_internet reliability=1
    src_lo = upsert_source(
        conn, company_id, kind="open_internet", uri="https://lo.example",
        writer="bob",
    )
    write_claims(conn, company_id, src_lo, [ClaimInput(field="country", value="LowRelCountry")], writer="bob")
    write_claims(conn, company_id, src_hi, [ClaimInput(field="country", value="HighRelCountry")], writer="alice")

    rec = to_airtable_record(conn, company_id)
    assert rec["country"] == "HighRelCountry"


def test_equal_reliability_newest_wins(conn):
    company_id = resolve_company(conn, "JPM/Beta/deck.pdf", "Beta Inc", "JPM 2026")
    # two sources, same kind => same reliability (3)
    src_a = upsert_source(conn, company_id, kind="company_submitted", uri="https://a.example", writer="alice")
    src_b = upsert_source(conn, company_id, kind="company_submitted", uri="https://b.example", writer="bob")
    write_claims(conn, company_id, src_a, [ClaimInput(field="indication", value="OldValue")], writer="alice")
    time.sleep(0.01)  # guarantee distinct created_at ordering
    write_claims(conn, company_id, src_b, [ClaimInput(field="indication", value="NewValue")], writer="bob")

    rec = to_airtable_record(conn, company_id)
    assert rec["indication"] == "NewValue"


def test_output_keys_subset_of_field_map_and_has_company_event(conn):
    company_id = resolve_company(conn, "JPM/Gamma/deck.pdf", "Gamma Inc", "JPM 2026")
    src = upsert_source(conn, company_id, kind="company_submitted", uri=None, writer="alice")
    write_claims(
        conn, company_id, src,
        [
            ClaimInput(field="country", value="USA"),
            ClaimInput(field="medical_field", value="Nephrology"),
        ],
        writer="alice",
    )

    rec = to_airtable_record(conn, company_id)
    # company + event always present
    assert "company" in rec and "event" in rec
    assert rec["event"] == "JPM 2026"
    # every key must be a valid FIELD_MAP json_key
    assert set(rec).issubset(set(FIELD_MAP))
    # only fields that have a claim appear (plus company/event)
    assert set(rec) - {"company", "event"} == {"country", "medical_field"}
    assert rec["country"] == "USA"
    assert rec["medical_field"] == "Nephrology"
