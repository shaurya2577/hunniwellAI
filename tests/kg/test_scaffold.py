import os

import psycopg
import pytest

from kg.models import Claim, ClaimInput, DEFAULT_RELIABILITY


def test_default_reliability_has_seven_kinds_with_correct_ints():
    assert DEFAULT_RELIABILITY == {
        "internal_notes": 5,
        "third_party": 4,
        "company_submitted": 3,
        "pitch_deck": 3,
        "medical_journal": 3,
        "web_social": 2,
        "open_internet": 1,
    }
    assert all(isinstance(v, int) for v in DEFAULT_RELIABILITY.values())


def test_claim_input_defaults():
    ci = ClaimInput(field="hq_city", value="Boston")
    assert ci.field == "hq_city"
    assert ci.value == "Boston"
    assert ci.confidence is None


def test_claim_input_accepts_confidence():
    ci = ClaimInput(field=None, value="x", confidence=0.5)
    assert ci.field is None
    assert ci.confidence == 0.5


def test_claim_dataclass_fields():
    c = Claim(
        id="clm_" + "a" * 32,
        company_id="00000000-0000-0000-0000-000000000000",
        field="hq_city",
        value="Boston",
        source_id=None,
        writer="ingest",
        confidence=None,
        status="active",
        reliability=3,
        source_uri=None,
        source_kind="company_submitted",
    )
    assert c.id == "clm_" + "a" * 32
    assert c.status == "active"
    assert c.reliability == 3


def test_get_db_url_falls_back_to_supabase_when_test_empty(monkeypatch):
    from kg import config

    monkeypatch.setenv("TEST_DATABASE_URL", "")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://x/prod")
    assert config.get_db_url() == "postgresql://x/prod"


def test_get_db_url_prefers_test_database_url(monkeypatch):
    from kg import config

    # Both set: TEST_DATABASE_URL must win (the genuine preference).
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://x/test")
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://x/prod")
    assert config.get_db_url() == "postgresql://x/test"


def test_connect_returns_live_connection():
    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/hunniwell_test",
    )
    conn = psycopg.connect(url)
    try:
        from pgvector.psycopg import register_vector

        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("select 1")
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
