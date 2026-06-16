import uuid

from kg.companies import resolve_company
from kg.sources import upsert_source

def _company(conn) -> str:
    return resolve_company(conn, relpath="events/x/acme.md", name="Acme Inc", event="x")

def _row(conn, source_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "select kind, reliability, uri, tag, title, writer "
            "from sources where id = %s",
            (source_id,),
        )
        return cur.fetchone()

def test_upsert_source_returns_uuid(conn):
    cid = _company(conn)
    sid = upsert_source(conn, cid, "company_submitted", "file://deck.pdf", writer="ingest")
    # is a parseable uuid string
    assert str(uuid.UUID(sid)) == sid
    assert _row(conn, sid) is not None

def test_default_reliability_from_map(conn):
    cid = _company(conn)
    sid = upsert_source(conn, cid, "open_internet", "http://x.com", writer="ingest")
    kind, reliability, *_ = _row(conn, sid)
    assert kind == "open_internet"
    assert reliability == 1  # DEFAULT_RELIABILITY["open_internet"]

def test_explicit_reliability_overrides_default(conn):
    cid = _company(conn)
    sid = upsert_source(
        conn, cid, "open_internet", "http://x.com", reliability=4, writer="ingest"
    )
    _kind, reliability, *_ = _row(conn, sid)
    assert reliability == 4

def test_tag_title_uri_writer_persisted(conn):
    cid = _company(conn)
    sid = upsert_source(
        conn,
        cid,
        "third_party",
        "http://crunchbase.com/acme",
        tag="EXT-1",
        title="Crunchbase profile",
        writer="alice",
    )
    kind, reliability, uri, tag, title, writer = _row(conn, sid)
    assert kind == "third_party"
    assert reliability == 4  # DEFAULT_RELIABILITY["third_party"]
    assert uri == "http://crunchbase.com/acme"
    assert tag == "EXT-1"
    assert title == "Crunchbase profile"
    assert writer == "alice"

def test_unknown_kind_stores_null_reliability(conn):
    cid = _company(conn)
    sid = upsert_source(conn, cid, "mystery_kind", None, writer="ingest")
    kind, reliability, uri, *_ = _row(conn, sid)
    assert kind == "mystery_kind"
    assert reliability is None  # no KeyError, NULL persisted
    assert uri is None
