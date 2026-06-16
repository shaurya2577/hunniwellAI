import re

import psycopg
import pytest

from kg.companies import _normalize_name, resolve_company

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Auvi Labs, Inc.", "auvilabs"),
        ("  Auvi   Labs  ", "auvilabs"),
        ("AUVI LABS LLC", "auvilabs"),
        ("Foo Corp.", "foo"),
        ("Bar Co", "bar"),
        ("Baz Ltd", "baz"),
        ("Acme Health Inc", "acmehealth"),
        ("plain name", "plainname"),
        ("Foo Corp, LLC", "foo"),
        # spacing/punctuation variants of the same company collapse to one key
        ("3D BioFibR Inc", "3dbiofibr"),
        ("3DBioFibR", "3dbiofibr"),
    ],
)
def test_normalize_name(raw, expected):
    assert _normalize_name(raw) == expected


def test_normalize_name_strips_stacked_suffixes():
    # Stacked legal suffixes must all be stripped so dedup works.
    assert _normalize_name("Foo Corp, LLC") == _normalize_name("Foo")


def _appearances(conn, company_id):
    with conn.cursor() as cur:
        cur.execute(
            "select relpath, event from company_appearances "
            "where company_id = %s order by relpath",
            (company_id,),
        )
        return cur.fetchall()


def _company_count(conn):
    with conn.cursor() as cur:
        cur.execute("select count(*) from companies")
        return cur.fetchone()[0]


def test_new_company_creates_one_row_and_appearance(conn):
    cid = resolve_company(
        conn, relpath="JPM 2026/Auvi Labs/deck.pdf", name="Auvi Labs, Inc.", event="JPM 2026"
    )
    assert UUID_RE.match(cid)
    assert _company_count(conn) == 1

    with conn.cursor() as cur:
        cur.execute(
            "select name_norm, name_raw from companies where id = %s", (cid,)
        )
        name_norm, name_raw = cur.fetchone()
    assert name_norm == "auvilabs"
    assert name_raw == "Auvi Labs, Inc."

    appearances = _appearances(conn, cid)
    assert appearances == [("JPM 2026/Auvi Labs/deck.pdf", "JPM 2026")]


def test_second_event_same_name_reuses_company_adds_appearance(conn):
    cid1 = resolve_company(
        conn, relpath="JPM 2026/Auvi Labs/deck.pdf", name="Auvi Labs, Inc.", event="JPM 2026"
    )
    cid2 = resolve_company(
        conn, relpath="LSI 2026/Auvi Labs/memo.md", name="AUVI LABS LLC", event="LSI 2026"
    )
    assert cid1 == cid2
    assert _company_count(conn) == 1

    appearances = _appearances(conn, cid1)
    # ordered by relpath asc: "JPM 2026/..." sorts before "LSI 2026/..."
    assert appearances == [
        ("JPM 2026/Auvi Labs/deck.pdf", "JPM 2026"),
        ("LSI 2026/Auvi Labs/memo.md", "LSI 2026"),
    ]


def test_two_relpaths_same_name_dedup_company(conn):
    cid1 = resolve_company(
        conn, relpath="evt/Foo Corp/a.pdf", name="Foo Corp.", event="evt"
    )
    cid2 = resolve_company(
        conn, relpath="evt/Foo/b.pdf", name="Foo", event="evt"
    )
    assert cid1 == cid2
    assert _company_count(conn) == 1
    assert len(_appearances(conn, cid1)) == 2


def test_spacing_variants_dedup_to_one_company(conn):
    # Real-data case from the LSI run: "3D BioFibR Inc" and "3DBioFibR" are the
    # same company in two folders; they must merge to one entity, two appearances.
    cid1 = resolve_company(conn, relpath="LSI/3D BioFibR Inc/a.pdf", name="3D BioFibR Inc", event="LSI")
    cid2 = resolve_company(conn, relpath="LSI/3DBioFibR/b.pdf", name="3DBioFibR", event="LSI")
    assert cid1 == cid2
    assert _company_count(conn) == 1
    assert len(_appearances(conn, cid1)) == 2


def test_same_relpath_twice_does_not_duplicate_appearance(conn):
    cid1 = resolve_company(
        conn, relpath="evt/Foo/a.pdf", name="Foo", event="evt"
    )
    cid2 = resolve_company(
        conn, relpath="evt/Foo/a.pdf", name="Foo", event="evt"
    )
    assert cid1 == cid2
    assert _company_count(conn) == 1
    assert len(_appearances(conn, cid1)) == 1
