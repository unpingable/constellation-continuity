"""Bounded CD2 historical-evidence example, using only Continuity's public API.

Run from a source checkout: PYTHONPATH=src python -m scripts.historical_trajectory
No classic installation, external effects, authority import, or automatic commit.
The default store is temporary; --db explicitly opts into retaining observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from continuity.api.models import (
    ActorRef, ObserveMemoryRequest, PremiseRef, QueryMemoryRequest, SourceRef,
)
from continuity.store.sqlite import SQLiteStore
from continuity.util.hashing import content_hash
from continuity.util.jsoncanon import canonical_json


FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/historical_cd2"
SCOPE = "case:historical-agent-gov-cd2"
NAMES = (
    "review_packet.json", "required_test_receipt.json",
    "validation.json", "current_disposition.json",
)


def _excerpt(record: dict) -> tuple[str, bool]:
    # Select existing source fields; never turn missing fields into verdicts.
    if "packet_id" in record:
        keys = ("packet_id", "playbook_id", "base_sha", "status", "design_notes")
    elif "receipt" in record:
        keys = ("receipt", "evidence")
    elif "subject" in record:
        keys = ("recorded_at", "basis", "evidence")
    else:
        keys = tuple(record)
    rendered = canonical_json({key: record[key] for key in keys if key in record})
    return rendered[:1600], len(rendered) > 1600


def ingest(store: SQLiteStore, fixture: Path = FIXTURE) -> list[str]:
    """Copy four pinned documents as observations; repeat safely after interruption.

    This is a specimen translation, not a supported classic format adapter.
    Foreign fields remain inert content. The actor identifies this copier, never
    the historical executor. Soft 'about' links associate evidence with the
    packet; they do not assert that an intervention caused a later outcome.
    """
    manifest = json.loads((fixture / "manifest.json").read_text())
    records = []
    # Validate all bytes before any write. Source paths are citations, never opened.
    for name in NAMES:
        raw = (fixture / name).read_bytes()
        info = manifest["files"][name]
        if hashlib.sha256(raw).hexdigest() != info["sha256"]:
            raise ValueError(f"historical source bytes differ: {name}")
        records.append((name, json.loads(raw), info))

    ids = []
    action = None
    for name, record, info in records:
        req = ObserveMemoryRequest(
            scope=SCOPE,
            kind="experiment" if action is None else "note",
            basis="import",
            content={"historical_record": record},
            source_refs=[
                SourceRef(
                    kind="git_blob",
                    ref=(f'{manifest["repository"]}/blob/{manifest["revision"]}/'
                         f'{info["source_path"]}'),
                    note="Historical checked-in record; its claims are not revalidated.",
                ),
                SourceRef(kind="sha256", ref=info["sha256"], note="Exact source file bytes."),
            ],
            premises=[] if action is None else [PremiseRef(
                memory_id=action.memory.memory_id, relation="about", strength="soft",
                pinned_content_hash=content_hash(action.memory),
                note="CD2 specimen association; not causal proof or acceptance.",
            )],
            actor=ActorRef(principal_id="tool:historical-trajectory-example", auth_method="local"),
            authoring_tier="runtime_authored",
        )
        # The existing store deduplicates keys, not request bodies. Bind the key
        # to the whole translation including sources, scope and premise identities.
        req.idempotency_key = "historical-example:" + hashlib.sha256(
            canonical_json(req.model_dump(mode="json")).encode()
        ).hexdigest()
        result = store.observe_memory(req)
        m = result.memory
        if (
            m.content != req.content or m.source_refs != req.source_refs
            or m.scope != req.scope or m.kind != req.kind or m.basis != req.basis
            or m.status != "observed" or m.reliance_class != "none"
            or m.authoring_tier != req.authoring_tier or m.created_by != req.actor
            or m.source_observed_at is not None
        ):
            raise ValueError("previous specimen observation changed; inspect its history")
        if action is None:
            action = result
        ids.append(m.memory_id)
    return ids


def retrieve(store: SQLiteStore, text: str = "state-index", limit: int = 3) -> dict:
    """Return at most three packet matches with bounded, attributed evidence cards.

    The scope and four-record specimen are deliberately fixed. This does not
    pretend to be a general trajectory index or a summary of arbitrary history.
    """
    if not 1 <= limit <= 3:
        raise ValueError("example limit must be between 1 and 3")
    matches = store.query_memory(QueryMemoryRequest(
        scope=SCOPE, kind="experiment", text=text, limit=limit,
    ))
    trajectories = []
    for action in matches.items:
        explained = store.explain_memory(action.memory_id)
        evidence = []
        links = [link for link in explained.dependents if link.relation == "about"]
        for link in links[:3]:
            m = store.get_memory(link.dst_memory_id)
            record = m.content.get("historical_record", {})
            # Card excerpts are verbatim JSON prefixes, not inferred verdicts.
            excerpt, truncated = _excerpt(record)
            evidence.append({
                "memory_id": m.memory_id,
                "memory_status": m.status,
                "source_refs": [s.model_dump(mode="json") for s in m.source_refs],
                "link": link.model_dump(mode="json"),
                "excerpt": excerpt,
                "excerpt_truncated": truncated,
            })
        excerpt, truncated = _excerpt(action.content["historical_record"])
        trajectories.append({
            "memory_id": action.memory_id,
            "memory_status": action.status,
            "reliance_class": action.reliance_class,
            "source_refs": [s.model_dump(mode="json") for s in action.source_refs],
            "match_reason": f"literal content JSON substring: {text}",
            "excerpt": excerpt,
            "excerpt_truncated": truncated,
            "evidence": evidence,
            "evidence_omitted": max(0, len(links) - 3),
        })
    return {
        "query": text, "total_matches": matches.total,
        "trajectories": trajectories,
        "caveat": (
            "Historical testimony only. A receipt pass, packet readiness, later reported "
            "landing, and Continuity memory status are distinct. Missing evidence is "
            "unknown, never success or failure. Full records: memory_get/memory_explain. "
            "This example does not verify external acceptance or identify an absent model/role."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="explicit store; default is temporary")
    parser.add_argument("--text", default="state-index", help="related-task literal search phrase")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="continuity-history-") as scratch:
        store = SQLiteStore(args.db or Path(scratch) / "history.db")
        store.initialize()
        ingest(store)
        print(json.dumps(retrieve(store, args.text), indent=2))


if __name__ == "__main__":
    main()
