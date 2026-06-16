# kg/ — per-company knowledge base

A relational claim store on **Supabase Postgres + pgvector**. Each extracted fact is a
*claim* tagged with its source and a reliability score; conflicting claims coexist
(never overwritten); citations resolve `claim_id -> source link` at output time; claims
carry embeddings for semantic search. Ingest writes into it, a council enriches it,
review queries it, and it exports back to the Airtable field shape.

## Public API (`from kg import ...`)
`resolve_company` · `upsert_source` · `write_claims` · `enrich` · `query` ·
`semantic_search` · `resolve_citation` · `validate_citations` · `to_airtable_record` · `connect`

---

## A. Just run the tests (NO secrets needed)

You need only **Python 3.12+** and **Docker**.

```bash
git clone <repo> && cd hunniwellAI
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# local Postgres + pgvector as the test DB (the test suite defaults to this URL)
docker run -d --name hunni-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=hunniwell_test -p 5432:5432 pgvector/pgvector:pg16

python -m pytest tests/kg/ -q     # expect: 80 passed
```

Tests use the local Postgres and **mock the embedder**, so no Supabase / Voyage / Anthropic
keys are involved. This is the fastest way for a new person to confirm the code works.

## B. Run the real pipeline (needs secrets + data)

1. **Env** — `cp .env.example .env` and fill in (see that file's comments; note the two
   `.env` locations). For local embeddings: `ollama pull mxbai-embed-large` and keep
   `EMBEDDINGS_PROVIDER=ollama`. For Voyage: set `EMBEDDINGS_PROVIDER=voyage` + `VOYAGE_API_KEY`.
2. **Pick a database:**
   - *Local* — keep using the Docker `hunni-pg` above (set nothing else).
   - *Supabase* — put the Session-pooler `SUPABASE_DB_URL` in `.env`, then apply the schema:
     ```python
     from kg.config import connect, apply_schema
     c = connect(); c.execute("create extension if not exists vector"); c.commit(); apply_schema(c)
     ```
3. **Get the source decks** — the per-company files live on OneDrive, not in git. Sync them
   locally and set `HUNNIWELL_COMPANYFILES_ROOT` (or pass `--root`).
4. **Ingest into the KG** (also writes Airtable):
   ```bash
   python -m ai.airtable_ingest.ingest --kg --event "<event folder name>"
   ```
   `--kg` mirrors each extracted record into the KG after the Airtable write. Omit `--kg`
   (and `SUPABASE_DB_URL`) to run the original Airtable-only ingest.

## Schema
4 tables (`kg/schema.sql`): `companies`, `company_appearances` (relpath = idempotency key),
`sources` (kind + reliability + uri), `claims` (`clm_*` id, value, source_id, writer,
`embedding vector(1024)`, status). Reliability defaults by source kind:
internal_notes 5 · third_party 4 · company_submitted 3 · web_social 2 · open_internet 1.

## Embeddings
`EMBEDDINGS_PROVIDER` switches backend with **no schema change** (both are 1024-dim):
`ollama` (local `mxbai-embed-large`, free) or `voyage` (`voyage-3.5`, needs a key).
