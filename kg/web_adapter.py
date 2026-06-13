import re

from .models import ClaimInput
from .sources import upsert_source
from .claims import write_claims

_REF_RE = re.compile(r"^\[(INT-\d+|EXT-\d+)\]\s+(.*?)\s*$")
_TAG_RE = re.compile(r"\[(INT-\d+|EXT-\d+)\]")

# Common abbreviations whose trailing period must NOT end a sentence.
_ABBREVS = (
    "Dr", "Mr", "Mrs", "Ms", "Prof", "St", "vs", "etc", "Inc", "Corp",
    "Ltd", "Co", "U.S", "U.K", "Ph.D", "e.g", "i.e", "No",
)
# Sentence boundary: end punctuation + whitespace + an uppercase/'[' start, but
# NOT after a known abbreviation and NOT inside a decimal like "4.2" (the period
# is only a boundary when followed by whitespace, so "4.2M" never splits). The
# split position is just AFTER the period, so each abbreviation guard includes
# its trailing period, e.g. (?<!\bDr\.).
_ABBREV_GUARD = "".join(
    r"(?<!\b" + a.replace(".", r"\.") + r"\.)" for a in _ABBREVS
)
_SENT_SPLIT_RE = re.compile(_ABBREV_GUARD + r"(?<=[.!?])\s+(?=[A-Z\[])")


def _split_ref_line(rest: str):
    """Return (title, uri). EXT lines look like 'Title — URL' or 'Title - URL'."""
    m = re.search(r"\s[—-]\s+(\S+://\S+)\s*$", rest)
    if m:
        return rest[: m.start()].strip(), m.group(1).strip()
    return rest.strip(), rest.strip()


def parse_memo(text: str) -> dict:
    lines = text.splitlines()
    references: dict[str, dict] = {}
    ref_start = None
    for i, line in enumerate(lines):
        if line.strip().upper() == "REFERENCES":
            ref_start = i + 1
            break

    if ref_start is not None:
        for line in lines[ref_start:]:
            m = _REF_RE.match(line.strip())
            if not m:
                continue
            tag, rest = m.group(1), m.group(2)
            title, uri = _split_ref_line(rest)
            kind = "company_submitted" if tag.startswith("INT") else "open_internet"
            references[tag] = {"uri": uri, "title": title, "kind": kind}

    body_lines = lines if ref_start is None else lines[: ref_start - 1]
    body = "\n".join(body_lines)

    # Segment the body into sentences (per line, so a sentence never crosses a
    # newline), then keep only sentences carrying an [INT-n]/[EXT-n] tag. Using a
    # period-aware splitter (not a [^.\n]* class) so decimals ("$4.2M") and
    # abbreviations ("Dr. Smith") are not truncated.
    claims: list[dict] = []
    for line in body.splitlines():
        if not line.strip():
            continue
        for stmt in _SENT_SPLIT_RE.split(line):
            tags = _TAG_RE.findall(stmt)
            if not tags:
                continue
            value = _TAG_RE.sub("", stmt).strip()
            value = re.sub(r"\s+", " ", value).strip()
            claims.append({"field": None, "value": value, "tags": sorted(set(tags))})

    return {"references": references, "claims": claims}


def ingest_memo(conn, company_id: str, memo_text: str, memo_path: str) -> list[str]:
    """Parse a web_ingest memo and write one source per referenced tag plus one
    claim per cited statement, linking each claim to the source of its primary
    (first sorted) tag. Returns the written claim ids."""
    parsed = parse_memo(memo_text)
    references = parsed["references"]

    tag_source: dict[str, str] = {}
    for tag, ref in references.items():
        source_id = upsert_source(
            conn,
            company_id,
            ref["kind"],
            ref["uri"],
            tag=tag,
            title=ref["title"],
            writer="web_ingest",
        )
        tag_source[tag] = source_id

    written: list[str] = []
    for c in parsed["claims"]:
        primary_tag = c["tags"][0] if c["tags"] else None
        source_id = tag_source.get(primary_tag)
        if source_id is None:
            continue
        ids = write_claims(
            conn,
            company_id,
            source_id,
            [ClaimInput(field=c["field"], value=c["value"])],
            writer="web_ingest",
        )
        written.extend(ids)
    return written
