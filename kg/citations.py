import re

import psycopg

CITATION_RE = re.compile(r"\[\[(clm_[0-9a-f]{32})\]\]")


def resolve_citation(conn: psycopg.Connection, claim_id: str) -> dict:
    """Resolve an active claim id to its citation record.

    Raises KeyError if no active claim with that id exists.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            select c.id, c.value, s.uri, s.kind, s.reliability
            from claims c
            left join sources s on s.id = c.source_id
            where c.id = %s and c.status = 'active'
            """,
            (claim_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise KeyError(claim_id)
    return {
        "claim_id": row[0],
        "value": row[1],
        "source_uri": row[2],
        "source_kind": row[3],
        "reliability": row[4],
    }


def validate_citations(conn: psycopg.Connection, text: str, company_id: str) -> list[str]:
    """Return citation tokens in `text` that do NOT resolve to an active claim
    for `company_id`. Order-preserving and de-duplicated.
    """
    tokens: list[str] = []
    seen: set[str] = set()
    for tok in CITATION_RE.findall(text):
        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)
    if not tokens:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            select id from claims
            where status = 'active'
              and company_id = %s
              and id = any(%s)
            """,
            (company_id, tokens),
        )
        valid = {r[0] for r in cur.fetchall()}
    return [t for t in tokens if t not in valid]
