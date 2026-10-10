"""Historical testimony round trip, association, bounds, and absence semantics."""

import json
import shutil
import sqlite3

import pytest

from scripts.historical_trajectory import FIXTURE, NAMES, SCOPE, ingest, retrieve
from continuity.api.models import QueryMemoryRequest, RepairMemoryRequest, RevokeMemoryRequest


def test_historical_bytes_provenance_and_outcome_round_trip(store):
    ids = ingest(store)
    for name, mid in zip(NAMES, ids):
        memory = store.get_memory(mid)
        assert memory.content["historical_record"] == json.loads((FIXTURE / name).read_text())
        info = json.loads((FIXTURE / "manifest.json").read_text())["files"][name]
        assert memory.source_refs[1].ref == info["sha256"]
        assert memory.source_refs[0].ref.endswith(info["source_path"])
        assert memory.status == "observed"
        assert memory.reliance_class == "none"
        assert memory.approved_by is None
        assert memory.source_observed_at is None  # don't invent historical occurrence time
        assert not store.explain_memory(mid).rely_ok
    for mid in ids[1:]:
        link = store.explain_memory(mid).premises[0]
        assert link.src_memory_id == ids[0]
        assert (link.relation, link.strength) == ("about", "soft")
        assert link.pinned_content_hash
    result = retrieve(store, "STATE-INDEX")
    assert result["total_matches"] == 1
    trajectory = result["trajectories"][0]
    assert trajectory["memory_id"] == ids[0]
    assert "proposed_patch" in trajectory["excerpt"]
    assert {e["memory_id"] for e in trajectory["evidence"]} == set(ids[1:])
    assert "valid_and_ready" in json.dumps(trajectory["evidence"])
    assert "ca63a34" in json.dumps(trajectory["evidence"])
    assert len(json.dumps(result)) < 12000
    assert all(len(e["excerpt"]) <= 1600 for e in trajectory["evidence"])


def test_duplicate_ingestion_adds_no_rows_or_receipts(store):
    ids = ingest(store)
    with sqlite3.connect(store.db_path) as conn:
        before = [conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in ("memory_objects", "memory_events", "receipts", "memory_links")]
    assert ingest(store) == ids
    with sqlite3.connect(store.db_path) as conn:
        after = [conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                 for table in ("memory_objects", "memory_events", "receipts", "memory_links")]
    assert before == after == [4, 4, 4, 3]


def test_changed_source_refused_before_writing(store, tmp_path):
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE, fixture)
    (fixture / NAMES[-1]).write_text("{}")
    with pytest.raises(ValueError, match="source bytes differ"):
        ingest(store, fixture)
    assert store.query_memory(QueryMemoryRequest()).total == 0


def test_duplicate_does_not_mask_repaired_observation(store):
    mid = ingest(store)[0]
    store.repair_memory(RepairMemoryRequest(
        memory_id=mid, reason="negative qualification case",
        patch={"content": {"historical_record": {"status": "different"}}},
    ))
    with pytest.raises(ValueError, match="observation changed"):
        ingest(store)


def test_absence_and_revocation_are_not_execution_outcomes(store):
    assert retrieve(store)["total_matches"] == 0
    ids = ingest(store)
    assert retrieve(store, "unrelated-task")["trajectories"] == []
    store.revoke_memory(RevokeMemoryRequest(memory_id=ids[-1], reason="disputed testimony"))
    result = retrieve(store)
    revoked = next(e for e in result["trajectories"][0]["evidence"] if e["memory_id"] == ids[-1])
    assert revoked["memory_status"] == "revoked"
    assert "landing_commit" in revoked["excerpt"]  # original reported outcome survives
    assert "Missing evidence is unknown" in result["caveat"]
    with pytest.raises(ValueError, match="observation changed"):
        ingest(store)


def test_retrieval_without_later_evidence_does_not_claim_an_outcome(store):
    # Only the action observation exists; later records have not arrived.
    from continuity.api.models import ObserveMemoryRequest
    store.observe_memory(ObserveMemoryRequest(
        scope=SCOPE, kind="experiment", basis="import",
        content={"historical_record": {"playbook_id": "state-index"}},
    ))
    card = retrieve(store)["trajectories"][0]
    assert card["evidence"] == []
    assert "pass" not in card["excerpt"] and "fail" not in card["excerpt"]
    with pytest.raises(ValueError):
        retrieve(store, limit=4)
