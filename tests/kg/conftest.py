from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from pgvector.psycopg import register_vector

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/hunniwell_test",
)

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "kg" / "schema.sql"
_TABLES = ("claims", "sources", "company_appearances", "companies")


@pytest.fixture(scope="session")
def _session_conn():
    conn = psycopg.connect(TEST_DATABASE_URL)
    register_vector(conn)
    # schema.sql is authored in Task 2; apply lazily/guarded so Task 1 passes.
    if _SCHEMA_PATH.exists():
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_PATH.read_text())
        conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def conn(_session_conn):
    # Truncate before EACH test (only if schema/tables exist yet).
    with _session_conn.cursor() as cur:
        cur.execute(
            "select to_regclass('public.companies') is not null"
        )
        have_tables = cur.fetchone()[0]
        if have_tables:
            cur.execute(
                "truncate "
                + ", ".join(_TABLES)
                + " restart identity cascade"
            )
    _session_conn.commit()
    yield _session_conn
