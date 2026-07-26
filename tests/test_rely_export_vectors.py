"""Golden vectors for continuity.rely_export.v0.

The bytes are the contract; consumers (NQ's `continuity_rely_record` import
profile) verify these same files independently. Each vector is internally
consistent: its export_id recomputes from its own core, its rely code is in
the closed vocabulary, and no authority-shaped key appears.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from continuity.declaration_export import FORBIDDEN_EXPORT_FIELDS
from continuity.rely_export import SCHEMA, compute_export_id

VECTOR_DIR = Path(__file__).parent / "fixtures" / "rely_export_vectors"
KNOWN_CODES = {
    "eligible", "status_not_committed", "expired", "reliance_none",
    "authoring_tier_capped", "kind_basis_policy", "hard_premise_unavailable",
}


def vectors() -> list[Path]:
    files = sorted(VECTOR_DIR.glob("*.json"))
    assert len(files) >= 6
    return files


@pytest.mark.parametrize("path", vectors(), ids=lambda p: p.name)
def test_vector_is_internally_consistent(path: Path) -> None:
    doc = json.loads(path.read_text())
    assert doc["schema"] == SCHEMA
    assert doc["export_id"] == compute_export_id(doc)
    assert doc["rely"]["code"] in KNOWN_CODES
    assert doc["source"]["system"] == "continuity"
    assert doc["subject"]["memory_id"].startswith("mem_")
    assert doc["content_hash"].startswith("sha256:")
    assert doc["does_not_establish"], "mandatory limits must be present"


@pytest.mark.parametrize("path", vectors(), ids=lambda p: p.name)
def test_vector_carries_no_authority_keys(path: Path) -> None:
    doc = json.loads(path.read_text())

    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield str(k).lower()
                yield from keys(v)
        elif isinstance(obj, list):
            for i in obj:
                yield from keys(i)

    hits = {k for k in keys(doc) if k in FORBIDDEN_EXPORT_FIELDS}
    assert not hits, hits


def test_vector_set_covers_the_required_outcomes() -> None:
    codes = {}
    for path in vectors():
        doc = json.loads(path.read_text())
        codes.setdefault(doc["rely"]["code"], []).append(path.name)
    assert "eligible" in codes
    assert "status_not_committed" in codes  # both flavors below
    flavors = set()
    for path in vectors():
        doc = json.loads(path.read_text())
        if doc["rely"]["code"] == "status_not_committed":
            flavors.add(doc["rely"]["details"]["status"])
        if doc["rely"]["code"] == "hard_premise_unavailable":
            flavors.add("premise")
    # cannot-establish (observed) and discontinuity (revoked) both present,
    # never collapsed
    assert {"observed", "revoked"} <= flavors or "premise" in flavors


def test_altered_bytes_change_export_id() -> None:
    doc = json.loads((VECTOR_DIR / "01-eligible.json").read_text())
    doc["rely"]["rely_ok"] = False
    assert doc["export_id"] != compute_export_id(doc)
