import re

import psycopg

_LEGAL_SUFFIX_RE = re.compile(
    r"[\s,\.]+(?:inc|llc|ltd|corp|co)\b\.?$", re.IGNORECASE
)
_WS_RE = re.compile(r"\s+")
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_name(name: str) -> str:
    s = name.strip().lower()
    s = _WS_RE.sub(" ", s)
    # Strip stacked legal suffixes ("Foo Corp, LLC") by applying the regex
    # repeatedly until the string stops changing.
    while True:
        stripped = _LEGAL_SUFFIX_RE.sub("", s)
        if stripped == s:
            break
        s = stripped
    s = _WS_RE.sub(" ", s).strip()
    # Collapse to an alphanumeric-only dedup key so spacing/punctuation variants
    # of the same company merge (e.g. "3D BioFibR Inc" and "3DBioFibR" -> "3dbiofibr").
    return _NONALNUM_RE.sub("", s)


def resolve_company(conn: psycopg.Connection, relpath: str, name: str, event: str) -> str:
    name_norm = _normalize_name(name)
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into companies (name_norm, name_raw)
            values (%s, %s)
            on conflict (name_norm) do update set updated_at = now()
            returning id
            """,
            (name_norm, name),
        )
        company_id = cur.fetchone()[0]

        cur.execute(
            """
            insert into company_appearances (company_id, event, relpath)
            values (%s, %s, %s)
            on conflict (relpath) do nothing
            """,
            (company_id, event, relpath),
        )
    conn.commit()
    return str(company_id)
