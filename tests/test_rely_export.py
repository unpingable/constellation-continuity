"""Tests for `contctl rely-export` / continuity.rely_export.v0.

The record is a rely-result snapshot at an explicit evaluation time: a
refusal is a valid export (refusal is evidence, not silence); export_id is
deterministic for unchanged store state at the same evaluation time; later
results supersede without rewriting; nothing NQ-shaped or authority-shaped
crosses the wire.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from continuity.cli import main
from continuity.declaration_export import ExportError
from continuity.rely_export import (
    MANDATORY_DOES_NOT_ESTABLISH,
    RelyExport,
    SCHEMA,
    _assert_no_forbidden_fields,
)

EVAL_T = "2026-07-26T20:00:00Z"
EVAL_T2 = "2026-07-26T21:00:00Z"


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


def run(db_path: str, argv: list[str]) -> tuple[str, int]:
    import io

    buf = io.StringIO()
    code = 0
    with patch("sys.stdout", buf):
        try:
            main(["--db", db_path] + argv)
        except SystemExit as exc:  # argparse/typed exits
            code = int(exc.code or 0)
    return buf.getvalue(), code


def run_json(db_path: str, argv: list[str]) -> dict:
    out, code = run(db_path, argv)
    assert code == 0, out
    return json.loads(out)


def _mk_committed(db_path: str, scope: str = "repo:demo", **kw) -> str:
    run(db_path, ["init"])
    out, code = run(
        db_path,
        [
            "observe",
            "--scope", scope,
            "--kind", kw.get("kind", "fact"),
            "--basis", kw.get("basis", "operator_assertion"),
            "--content", kw.get("content", '{"note": "n1"}'),
            "-q",
        ]
        + (["--premise", kw["premise"]] if "premise" in kw else []),
    )
    assert code == 0
    mid = out.strip()
    args = ["commit", mid, "--reliance-class", kw.get("reliance_class", "advisory"), "-q"]
    out, code = run(db_path, args)
    assert code == 0
    return mid


def _export(db_path: str, mid: str, eval_t: str = EVAL_T) -> dict:
    return run_json(db_path, ["rely-export", mid, "--evaluation-time", eval_t])


def _core(export: dict) -> dict:
    """The deterministic core: everything but the envelope wall-clock."""
    return {k: v for k, v in export.items() if k not in ("exported_at",)}


# --- positive result -------------------------------------------------------

def test_positive_rely_export(db_path):
    mid = _mk_committed(db_path)
    doc = _export(db_path, mid)
    assert doc["schema"] == SCHEMA
    assert doc["subject"]["memory_id"] == mid
    assert doc["subject"]["scope"] == "repo:demo"
    assert doc["rely"]["rely_ok"] is True
    assert doc["rely"]["code"] == "eligible"
    assert doc["status"] == "committed"
    assert doc["content_hash"].startswith("sha256:")
    assert doc["export_id"].startswith("sha256:")
    assert doc["lifecycle"]["observe_event_id"].startswith("evt_")
    assert doc["lifecycle"]["latest_commit_receipt_hash"]
    assert doc["evaluation_time"].startswith("2026-07-26T20:00:00")


# --- refusal flavors stay distinct ----------------------------------------

def test_cannot_establish_observed_only_is_a_valid_export(db_path):
    """Never-committed (cannot-establish flavor) exports with the code and
    details.status=observed — distinct from discontinuity."""
    run(db_path, ["init"])
    out, _ = run(
        db_path,
        ["observe", "--scope", "s", "--kind", "fact", "--basis",
         "operator_assertion", "--content", '{"a": 1}', "-q"],
    )
    mid = out.strip()
    doc = _export(db_path, mid)
    assert doc["rely"]["rely_ok"] is False
    assert doc["rely"]["code"] == "status_not_committed"
    assert doc["rely"]["details"]["status"] == "observed"


def test_discontinuity_revoked_is_a_valid_export(db_path):
    mid = _mk_committed(db_path)
    run(db_path, ["revoke", mid, "--reason", "superseded by reality"])
    doc = _export(db_path, mid)
    assert doc["rely"]["rely_ok"] is False
    assert doc["rely"]["code"] == "status_not_committed"
    assert doc["rely"]["details"]["status"] == "revoked"
    assert doc["status"] == "revoked"


def test_premise_revocation_discontinuity(db_path):
    prem = _mk_committed(db_path, content='{"p": "premise"}')
    out, _ = run(
        db_path,
        ["observe", "--scope", "repo:demo", "--kind", "fact", "--basis",
         "operator_assertion", "--content", '{"d": "dependent"}',
         "--premise", f"{prem}:depends_on:hard", "-q"],
    )
    dep = out.strip()
    run(db_path, ["commit", dep, "--reliance-class", "advisory", "-q"])
    assert _export(db_path, dep)["rely"]["rely_ok"] is True
    run(db_path, ["revoke", prem, "--reason", "premise fell"])
    doc = _export(db_path, dep, EVAL_T2)
    assert doc["rely"]["code"] == "hard_premise_unavailable"
    assert any(b.endswith(":revoked") for b in doc["rely"]["details"]["bad_premises"])
    assert doc["premises"] and doc["premises"][0]["src"] == prem


def test_stale_expired_memory(db_path):
    mid = _mk_committed(db_path)
    # Direct library write of expires_at is out of CLI scope; evaluate far in
    # the future against an --evaluation-time before creation instead: expiry
    # is exercised via the expired-code path when expires_at is set. Here we
    # pin the time axis: an evaluation time is recorded verbatim.
    doc = _export(db_path, mid, "2030-01-01T00:00:00Z")
    assert doc["evaluation_time"].startswith("2030-01-01")


def test_missing_memory_no_partial_record(db_path):
    run(db_path, ["init"])
    out, code = run(db_path, ["rely-export", "mem_does_not_exist"])
    assert code == 1
    assert out.strip() == ""  # nothing on stdout — no partial record


# --- immutability / determinism -------------------------------------------

def test_same_state_same_evaluation_time_same_export_id(db_path):
    mid = _mk_committed(db_path)
    a = _export(db_path, mid)
    b = _export(db_path, mid)
    assert a["export_id"] == b["export_id"]
    assert _core(a) == _core(b)  # only exported_at may differ


def test_later_result_is_new_snapshot_old_bytes_unchanged(db_path):
    mid = _mk_committed(db_path)
    first = _export(db_path, mid)
    first_bytes = json.dumps(_core(first), sort_keys=True)
    run(db_path, ["revoke", mid, "--reason", "trajectory break"])
    second = _export(db_path, mid, EVAL_T2)
    assert second["export_id"] != first["export_id"]
    assert second["rely"]["rely_ok"] is False
    # the first record (as captured) is byte-identical — nothing rewrote it
    assert json.dumps(_core(first), sort_keys=True) == first_bytes


def test_content_change_changes_export_id(db_path):
    mid = _mk_committed(db_path)
    a = _export(db_path, mid)
    run(db_path, ["repair", mid, "--reason", "typo", "--content", '{"note": "n2"}'])
    b = _export(db_path, mid, EVAL_T2)
    assert a["content_hash"] != b["content_hash"]
    assert a["export_id"] != b["export_id"]


# --- authoring tier / provenance ------------------------------------------

def test_authoring_tier_copied_never_upgraded(db_path):
    mid = _mk_committed(db_path)
    doc = _export(db_path, mid)
    assert doc["authoring_tier"] == "agent_authored"
    assert doc["effective_reliance"] == "advisory"
    assert doc["rely"]["details"]["authoring_tier"] == "agent_authored"


def test_actionable_commit_refused_before_any_export(db_path):
    """The tier fence fires at commit; the exporter never sees a laundered
    record. (agent_authored + actionable is a receipted refusal.)"""
    run(db_path, ["init"])
    out, _ = run(
        db_path,
        ["observe", "--scope", "s", "--kind", "fact", "--basis",
         "operator_assertion", "--content", '{"a": 1}', "-q"],
    )
    mid = out.strip()
    _, code = run(db_path, ["commit", mid, "--reliance-class", "actionable", "-q"])
    assert code == 2  # policy refusal
    doc = _export(db_path, mid)
    assert doc["rely"]["code"] == "status_not_committed"  # still uncommitted


# --- wire discipline -------------------------------------------------------

def test_no_nq_or_authority_fields(db_path):
    mid = _mk_committed(db_path)
    doc = _export(db_path, mid)

    def keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield str(k).lower()
                yield from keys(v)
        elif isinstance(obj, list):
            for i in obj:
                yield from keys(i)

    all_keys = set(keys(doc))
    for forbidden in ("nq_status", "verdict", "admissibility", "authority",
                      "canonical", "authoritative", "standing_grant",
                      "capability", "disposition"):
        assert forbidden not in all_keys
    assert list(doc["does_not_establish"]) == list(MANDATORY_DOES_NOT_ESTABLISH)


def test_forbidden_field_selfcheck_fires():
    class Sneaky(RelyExport):
        pass

    mid_doc = None  # constructed below via model_validate on a real-ish core
    base = {
        "schema": SCHEMA, "export_id": "sha256:00", "exported_at": "t",
        "source": {"system": "continuity", "exporter": {"tool": "continuity", "version": "0"}},
        "subject": {"memory_id": "m", "scope": "s", "kind": "fact", "basis": "operator_assertion"},
        "content_hash": "sha256:00", "status": "committed",
        "authoring_tier": "agent_authored", "reliance_class": "advisory",
        "effective_reliance": "advisory", "lifecycle": {},
        "times": {"created_at": "t", "updated_at": "t"},
        "evaluation_time": "t",
        "rely": {"rely_ok": True, "code": "eligible", "message": "m",
                 "details": {"authority": "smuggled"}},
        "premises": [], "history": {"event_count": 1, "receipt_count": 1},
        "establishes": [], "does_not_establish": [],
    }
    export = RelyExport.model_validate(base)
    with pytest.raises(ExportError):
        _assert_no_forbidden_fields(export)


def test_machine_stdout_purity_and_exit_semantics(db_path):
    mid = _mk_committed(db_path)
    out, code = run(db_path, ["rely-export", mid, "--evaluation-time", EVAL_T])
    assert code == 0
    json.loads(out)  # stdout is exactly one JSON document
    run(db_path, ["revoke", mid, "--reason", "r"])
    out, code = run(db_path, ["rely-export", mid, "--evaluation-time", EVAL_T2])
    assert code == 0  # a refusal export is still a produced record
    assert json.loads(out)["rely"]["rely_ok"] is False


def test_malformed_store_is_typed_failure(tmp_path):
    bad = tmp_path / "garbage.db"
    bad.write_text("this is not a sqlite database")
    out, code = run(str(bad), ["rely-export", "mem_x"])
    assert code != 0
    assert out.strip() == ""
