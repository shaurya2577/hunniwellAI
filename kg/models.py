from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

DEFAULT_RELIABILITY: dict[str, int] = {
    "internal_notes": 5,
    "third_party": 4,
    "company_submitted": 3,
    "pitch_deck": 3,
    "medical_journal": 3,
    "web_social": 2,
    "open_internet": 1,
}


@dataclass
class Claim:
    id: str
    company_id: str
    field: Optional[str]
    value: str
    source_id: Optional[str]
    writer: str
    confidence: Optional[float]
    status: str
    reliability: Optional[int]
    source_uri: Optional[str]
    source_kind: Optional[str]


@dataclass
class ClaimInput:
    field: Optional[str]
    value: str
    confidence: Optional[float] = None
