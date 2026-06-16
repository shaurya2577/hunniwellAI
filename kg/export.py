"""Collapse a company's active claims into a single Airtable-shaped record.

Winner per field = highest source reliability, tie-broken by newest created_at.
Output is keyed by FIELD_MAP json_keys (only fields that have a claim) plus the
synthetic 'company' and 'event' keys taken from the company / its appearance.
"""

import psycopg

from ai.airtable_ingest.ingest import FIELD_MAP, _KG_SKIP_KEYS

# Claim fields eligible for export: every FIELD_MAP key EXCEPT the identity keys
# ('company','event','data_entry'), which are synthetic headers set from
# companies/appearances. A stray claim with field='company'/'event' must never
# overwrite those authoritative values. Mirrors the write-side _KG_SKIP_KEYS.
_EXPORT_FIELDS = [k for k in FIELD_MAP if k not in _KG_SKIP_KEYS]


def to_airtable_record(conn: psycopg.Connection, company_id: str) -> dict:
    rec: dict[str, str] = {}

    # company + event (event from the most recent appearance row).
    with conn.cursor() as cur:
        cur.execute("select name_raw from companies where id = %s", (company_id,))
        row = cur.fetchone()
        rec["company"] = row[0] if row else ""

        cur.execute(
            "select event from company_appearances "
            "where company_id = %s order by created_at desc limit 1",
            (company_id,),
        )
        ev = cur.fetchone()
        rec["event"] = ev[0] if ev else ""

        # One winning claim per field: highest reliability, then newest created_at.
        # NULL reliability sorts lowest so a known reliability always beats unknown.
        cur.execute(
            """
            select distinct on (c.field) c.field, c.value
            from claims c
            left join sources s on s.id = c.source_id
            where c.company_id = %s
              and c.status = 'active'
              and c.field is not null
              and c.field = any(%s)
            order by c.field,
                     coalesce(s.reliability, -1) desc,
                     c.created_at desc
            """,
            (company_id, _EXPORT_FIELDS),
        )
        for field, value in cur.fetchall():
            rec[field] = value

    return rec
