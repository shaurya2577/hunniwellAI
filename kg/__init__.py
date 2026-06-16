"""Public API for the kg/ company knowledge base.

Assembled ONCE here (Task 14). Backing modules:
  companies, sources, claims, search, citations, export, config, models.
"""
from __future__ import annotations

from kg.citations import resolve_citation, validate_citations
from kg.claims import enrich, query, write_claims
from kg.companies import resolve_company
from kg.config import connect
from kg.export import to_airtable_record
from kg.models import Claim, ClaimInput
from kg.search import semantic_search
from kg.sources import upsert_source

__all__ = [
    "resolve_company",
    "upsert_source",
    "write_claims",
    "enrich",
    "query",
    "semantic_search",
    "resolve_citation",
    "validate_citations",
    "to_airtable_record",
    "connect",
    "ClaimInput",
    "Claim",
]
