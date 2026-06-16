#!/usr/bin/env python3
"""Stand up the kg/ schema on a target Postgres (local Docker or your own Supabase).

Enables the pgvector extension and creates the 4 kg tables (idempotent — safe to re-run).

Usage:
    # uses TEST_DATABASE_URL, then SUPABASE_DB_URL, from your .env:
    python scripts/kg_apply_schema.py

    # or target an explicit database:
    python scripts/kg_apply_schema.py --db-url "postgresql://user:pwd@host:5432/postgres"

Local quick start (no secrets):
    docker run -d --name hunni-pg -e POSTGRES_PASSWORD=postgres \\
      -e POSTGRES_DB=hunniwell_test -p 5432:5432 pgvector/pgvector:pg16
    python scripts/kg_apply_schema.py
"""
import argparse
import os
import sys

# Make the repo root importable when run as a plain file.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from pgvector.psycopg import register_vector

from kg.config import apply_schema, get_db_url

EXPECTED = {"companies", "company_appearances", "sources", "claims"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply kg/schema.sql (enables pgvector) to a Postgres DB.")
    ap.add_argument("--db-url", help="Target DB URL. Defaults to TEST_DATABASE_URL then SUPABASE_DB_URL from .env.")
    args = ap.parse_args()

    url = args.db_url or get_db_url()
    where = url.split("@", 1)[1] if "@" in url else url  # never print the password
    print(f"Applying kg schema to ...@{where}")

    conn = psycopg.connect(url, connect_timeout=20)
    conn.execute("create extension if not exists vector")
    conn.commit()
    register_vector(conn)
    apply_schema(conn)
    have = {r[0] for r in conn.execute(
        "select tablename from pg_tables where schemaname='public'").fetchall()} & EXPECTED
    conn.close()

    print("Tables present:", sorted(have))
    if have >= EXPECTED:
        print("OK: kg schema ready.")
    else:
        print("ERROR: missing", sorted(EXPECTED - have))
        sys.exit(1)


if __name__ == "__main__":
    main()
