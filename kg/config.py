from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()


def get_db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "No database URL: set SUPABASE_DB_URL (or TEST_DATABASE_URL)."
        )
    return url


def get_voyage_key() -> str:
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY is not set.")
    return key


def connect() -> psycopg.Connection:
    conn = psycopg.connect(get_db_url())
    register_vector(conn)
    return conn
