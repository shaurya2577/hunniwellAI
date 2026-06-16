import pytest

from kg.companies import resolve_company
from kg.sources import upsert_source
from kg.claims import write_claims, enrich, query
from kg.models import ClaimInput

@pytest.fixture(autouse=True)
def _fake_embed(monkeypatch):
    def fake(texts):
        out = []
        for t in texts:
            seed = sum(ord(c) for c in t) or 1
            out.append([((seed * (i + 1)) % 1000) / 1000.0 for i in range(1024)])
        return out
    # Single module-attr patch; write_claims/enrich reach embed via embeddings.embed.
    monkeypatch.setattr("kg.embeddings.embed", fake)

def _setup_company_source(conn):
    company_id = resolve_company(conn, "deals/acme/memo.md", "Acme Inc", "Series A")
    source_id = upsert_source(
        conn, company_id, kind="internal_notes", uri=None, writer="analyst"
    )
    return company_id, source_id

def test_enrich_adds_new_active_claim_with_council_writer(conn):
    company_id, source_id = _setup_company_source(conn)

    ids = enrich(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston, MA")],
        writer="lucia",
    )
    assert len(ids) == 1
    assert ids[0].startswith("clm_")

    rows = query(conn, company_id, fields=["hq"])
    assert len(rows) == 1
    c = rows[0]
    assert c.id == ids[0]
    assert c.field == "hq"
    assert c.value == "Boston, MA"
    assert c.status == "active"
    # writer namespaced as council:<agent>
    assert c.writer == "council:lucia"

def test_enrich_does_not_double_prefix_council_writer(conn):
    # Caller passing an already-namespaced writer must not get "council:council:".
    company_id, source_id = _setup_company_source(conn)
    ids = enrich(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Austin, TX")],
        writer="council:lucia",
    )
    rows = query(conn, company_id, fields=["hq"])
    assert rows[0].writer == "council:lucia"


def test_supersede_marks_old_superseded_and_query_returns_only_new(conn):
    company_id, source_id = _setup_company_source(conn)

    old_ids = write_claims(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="stage", value="Seed")],
        writer="ingest",
    )
    assert len(old_ids) == 1
    old_id = old_ids[0]

    new_ids = enrich(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="stage", value="Series A")],
        writer="marcus",
        supersede_claim_ids=[old_id],
    )
    assert len(new_ids) == 1
    new_id = new_ids[0]
    assert new_id != old_id

    rows = query(conn, company_id, fields=["stage"])
    returned_ids = {r.id for r in rows}
    # old claim no longer active / not returned
    assert old_id not in returned_ids
    # new claim returned
    assert new_id in returned_ids
    assert len(rows) == 1
    assert rows[0].value == "Series A"
    assert rows[0].writer == "council:marcus"

    # old row marked superseded + superseded_by points to new id
    with conn.cursor() as cur:
        cur.execute(
            "select status, superseded_by from claims where id = %s", (old_id,)
        )
        status, superseded_by = cur.fetchone()
    assert status == "superseded"
    assert superseded_by == new_id

def test_enrich_does_not_self_supersede_returned_id(conn):
    # enrich's idempotent insert returns the EXISTING id on a claims_idem
    # conflict. If that same id is passed in supersede_claim_ids, the supersede
    # UPDATE must NOT retire the very claim it just returned (data loss).
    company_id, source_id = _setup_company_source(conn)

    first_ids = enrich(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston, MA")],
        writer="lucia",
    )
    assert len(first_ids) == 1
    the_id = first_ids[0]

    # Re-enrich the SAME (field, value, source); idempotent insert returns the
    # existing id. Pass that id as a supersede target.
    second_ids = enrich(
        conn,
        company_id,
        source_id,
        [ClaimInput(field="hq", value="Boston, MA")],
        writer="lucia",
        supersede_claim_ids=[the_id],
    )
    assert second_ids == [the_id]

    # The claim must STILL be active and returned by query().
    rows = query(conn, company_id, fields=["hq"])
    assert len(rows) == 1
    assert rows[0].id == the_id
    assert rows[0].value == "Boston, MA"
    assert rows[0].status == "active"


def test_supersede_failure_rolls_back_new_claim(conn):
    # Atomicity: if the supersede UPDATE fails, the new claim insert must roll
    # back too (nothing committed). psycopg3's Cursor.execute is read-only (a C
    # extension), so we cannot monkeypatch the method on a cursor instance.
    # Instead wrap the *connection* with a proxy whose cursor() yields a cursor
    # proxy that raises on the supersede UPDATE. enrich runs against the proxy,
    # which delegates everything (including commit/rollback) to the real conn,
    # so the rollback is exercised against the real Postgres transaction.
    company_id, source_id = _setup_company_source(conn)
    old_ids = write_claims(
        conn, company_id, source_id, [ClaimInput(field="stage", value="Seed")], writer="ingest"
    )

    class _Boom(Exception):
        pass

    class _CursorProxy:
        def __init__(self, cur):
            self._cur = cur

        def execute(self, sql, params=None):
            if "set status = 'superseded'" in sql:
                raise _Boom("simulated supersede failure")
            if params is not None:
                return self._cur.execute(sql, params)
            return self._cur.execute(sql)

        def __enter__(self):
            self._cur.__enter__()
            return self

        def __exit__(self, *exc):
            return self._cur.__exit__(*exc)

        def __getattr__(self, name):
            return getattr(self._cur, name)

    class _ConnProxy:
        def __init__(self, real):
            self._real = real

        def cursor(self, *a, **k):
            return _CursorProxy(self._real.cursor(*a, **k))

        def __getattr__(self, name):
            return getattr(self._real, name)

    proxy = _ConnProxy(conn)

    import pytest as _pytest
    with _pytest.raises(_Boom):
        enrich(
            proxy,
            company_id,
            source_id,
            [ClaimInput(field="stage", value="Series A")],
            writer="marcus",
            supersede_claim_ids=[old_ids[0]],
        )

    # The new "Series A" claim must NOT have been committed; old still active.
    rows = query(conn, company_id, fields=["stage"])
    assert {r.value for r in rows} == {"Seed"}
