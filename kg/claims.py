from __future__ import annotations

from uuid import uuid4

from pgvector.psycopg import Vector

from kg import embeddings  # module-attr import: callers use embeddings.embed(...)
from kg.models import ClaimInput


def _new_claim_id() -> str:
    return "clm_" + uuid4().hex


def write_claims(conn, company_id, source_id, claims, writer):
    """Insert claims idempotently. Embeds each value via kg.embeddings.embed.

    The embed call site is ALWAYS the module attr `embeddings.embed(...)` so a
    single test patch of `kg.embeddings.embed` intercepts every caller. There is
    no `kg.claims.embed` symbol.

    Idempotency is enforced by the partial unique index claims_idem on
    (company_id, coalesce(field,''), md5(value), source_id) where status='active'.
    A re-insert of the same (field, value, source) returns the existing id and
    creates no duplicate row.
    """
    if not claims:
        return []

    values = [c.value for c in claims]
    vectors = embeddings.embed(values)

    out: list[str] = []
    with conn.cursor() as cur:
        for claim, vec in zip(claims, vectors):
            new_id = _new_claim_id()
            cur.execute(
                # The ON CONFLICT target+predicate below MUST mirror the schema's
                # claims_idem partial-index expression
                #   (company_id, coalesce(field,''), md5(value), source_id)
                # and predicate  WHERE status = 'active'  EXACTLY. Any divergence
                # makes Postgres raise: "there is no unique or exclusion constraint
                # matching the ON CONFLICT specification".
                """
                insert into claims
                    (id, company_id, field, value, source_id, writer, confidence, embedding, status)
                values
                    (%s, %s, %s, %s, %s, %s, %s, %s, 'active')
                on conflict (company_id, coalesce(field,''), md5(value), source_id)
                    where status = 'active'
                do nothing
                returning id
                """,
                (
                    new_id,
                    company_id,
                    claim.field,
                    claim.value,
                    source_id,
                    writer,
                    claim.confidence,
                    Vector(vec),
                ),
            )
            row = cur.fetchone()
            if row is not None:
                out.append(row[0])
            else:
                # Conflict: an active row already exists; fetch its id.
                cur.execute(
                    """
                    select id from claims
                    where company_id = %s
                      and coalesce(field, '') = coalesce(%s, '')
                      and md5(value) = md5(%s)
                      and source_id = %s
                      and status = 'active'
                    """,
                    (company_id, claim.field, claim.value, source_id),
                )
                out.append(cur.fetchone()[0])
    conn.commit()
    return out
