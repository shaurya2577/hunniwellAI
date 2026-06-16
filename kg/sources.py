from typing import Optional

import psycopg

from kg.models import DEFAULT_RELIABILITY


def upsert_source(
    conn: psycopg.Connection,
    company_id: str,
    kind: str,
    uri: Optional[str],
    *,
    tag: Optional[str] = None,
    reliability: Optional[int] = None,
    title: Optional[str] = None,
    writer: str,
) -> str:
    """Insert a source row, defaulting reliability from DEFAULT_RELIABILITY[kind].

    Returns the new source id (uuid string). When reliability is None and kind
    is unknown, reliability is stored as NULL (no KeyError).
    """
    if reliability is None:
        reliability = DEFAULT_RELIABILITY.get(kind)

    with conn.cursor() as cur:
        cur.execute(
            """
            insert into sources (company_id, kind, reliability, uri, tag, title, writer)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning id
            """,
            (company_id, kind, reliability, uri, tag, title, writer),
        )
        source_id = cur.fetchone()[0]
    conn.commit()
    return str(source_id)
