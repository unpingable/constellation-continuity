"""Conformance tests for the Docket -> Continuity subject contract."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from continuity.api.models import (
    CommitMemoryRequest,
    MemoryStatus,
    QueryMemoryRequest,
    RelianceClass,
    RevokeMemoryRequest,
)
from continuity.cli import main
from continuity.ref_continuity import (
    DocketProvenance,
    REF_CONTINUITY_CONTRACT,
    RefContinuityBindingError,
    RefContinuityObservationRequest,
    RepositoryId,
    bind_ref_continuity_subject,
    build_ref_continuity_observe_request,
    observe_ref_continuity,
)
from continuity.store.sqlite import SQLiteStore


REPOSITORY_ID = "repo-" + "11" * 16
TARGET_REF = "refs/gwr/target"
RESULT_COMMIT = "0123456789abcdef0123456789abcdef01234567"
RESULT_COMMIT_SHA256 = RESULT_COMMIT + "89abcdef0123456789abcdef"
PREPARED_DIGEST = "ab" * 32
ATTEMPT_ID = "att-" + "22" * 16
SUBJECT = (
    f"gwr:ref-continuity:v0:{REPOSITORY_ID}"
    f"#{TARGET_REF}@{RESULT_COMMIT}"
)


def _request(
    *,
    subject: str = SUBJECT,
    repository_id: str = REPOSITORY_ID,
    target_ref: str = TARGET_REF,
    result_commit: str = RESULT_COMMIT,
    idempotency_key: str | None = None,
) -> RefContinuityObservationRequest:
    return RefContinuityObservationRequest(
        subject=subject,
        repository_id=RepositoryId(repository_id),
        target_ref=target_ref,
        result_commit=result_commit,
        docket=DocketProvenance(
            attempt_id=ATTEMPT_ID,
            dossier_version=4,
            prepared_attempt_digest=PREPARED_DIGEST,
        ),
        idempotency_key=idempotency_key,
    )


def _store(path: Path) -> SQLiteStore:
    store = SQLiteStore(path)
    store.initialize(scope_kind="explicit")
    return store


def _run_cli(db: Path, argv: list[str]) -> tuple[str, str, int]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = 0
    with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
        try:
            main(["--db", str(db), *argv])
        except SystemExit as exc:
            code = int(exc.code)
    return stdout.getvalue(), stderr.getvalue(), code


def _cli_args(*, repository_id: str = REPOSITORY_ID) -> list[str]:
    return [
        "observe-ref-continuity",
        "--subject",
        SUBJECT,
        "--repository-id",
        repository_id,
        "--target-ref",
        TARGET_REF,
        "--result-commit",
        RESULT_COMMIT,
        "--docket-attempt",
        ATTEMPT_ID,
        "--dossier-version",
        "4",
        "--prepared-attempt-digest",
        PREPARED_DIGEST,
    ]


def test_exact_supplied_subject_is_bound_and_returned() -> None:
    repository_id = RepositoryId(REPOSITORY_ID)
    binding = bind_ref_continuity_subject(
        supplied_subject=SUBJECT,
        repository_id=repository_id,
        target_ref=TARGET_REF,
        result_commit=RESULT_COMMIT,
    )

    assert binding.subject is SUBJECT
    assert binding.repository_id == repository_id
    assert binding.target_ref == TARGET_REF
    assert binding.result_commit == RESULT_COMMIT


@pytest.mark.parametrize(
    "locator",
    [
        "/home/operator/repository",
        "./repository",
        "../repository",
        r"C:\work\repository",
        "file:///work/repository",
        "https://example.invalid/org/repository.git",
        "git@example.invalid:org/repository.git",
    ],
)
def test_path_remote_or_checkout_locator_is_rejected_as_repository_id(
    locator: str,
) -> None:
    with pytest.raises(RefContinuityBindingError, match="RepositoryId|locator|path"):
        RepositoryId(locator)


@pytest.mark.parametrize(
    "repository_id",
    [
        "repo-nightshift",
        "11" * 16,
        "repo-" + "A1" * 16,
        "repo-" + "11" * 15,
        "repo-" + "11" * 17,
    ],
)
def test_only_opaque_typed_repository_id_wire_is_accepted(
    repository_id: str,
) -> None:
    with pytest.raises(RefContinuityBindingError, match="opaque Docket wire"):
        RepositoryId(repository_id)


@pytest.mark.parametrize(
    "target_ref",
    [
        "gwr/target",
        "refs/",
        " refs/gwr/target",
        "refs/gwr/target ",
        "refs/gwr//target",
        "refs/gwr/../target",
        "refs/gwr/target.lock",
        "refs/gwr/target~1",
    ],
)
def test_target_ref_must_be_exact_and_fully_qualified(target_ref: str) -> None:
    subject = (
        f"gwr:ref-continuity:v0:{REPOSITORY_ID}"
        f"#{target_ref}@{RESULT_COMMIT}"
    )
    with pytest.raises(RefContinuityBindingError, match="target_ref"):
        bind_ref_continuity_subject(
            supplied_subject=subject,
            repository_id=RepositoryId(REPOSITORY_ID),
            target_ref=target_ref,
            result_commit=RESULT_COMMIT,
        )


@pytest.mark.parametrize(
    "result_commit",
    [
        "0123456",
        "A" * 40,
        "g" * 40,
        "0" * 39,
        "0" * 41,
        "0" * 63,
        "0" * 65,
    ],
)
def test_result_commit_must_be_exact_full_lowercase_hex(
    result_commit: str,
) -> None:
    with pytest.raises(RefContinuityBindingError, match="result_commit"):
        bind_ref_continuity_subject(
            supplied_subject=(
                f"gwr:ref-continuity:v0:{REPOSITORY_ID}"
                f"#{TARGET_REF}@{result_commit}"
            ),
            repository_id=RepositoryId(REPOSITORY_ID),
            target_ref=TARGET_REF,
            result_commit=result_commit,
        )


def test_full_sha256_commit_is_accepted_without_normalization() -> None:
    subject = (
        f"gwr:ref-continuity:v0:{REPOSITORY_ID}"
        f"#{TARGET_REF}@{RESULT_COMMIT_SHA256}"
    )
    binding = bind_ref_continuity_subject(
        supplied_subject=subject,
        repository_id=RepositoryId(REPOSITORY_ID),
        target_ref=TARGET_REF,
        result_commit=RESULT_COMMIT_SHA256,
    )
    assert binding.subject == subject
    assert binding.result_commit == RESULT_COMMIT_SHA256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", "repo-" + "33" * 16),
        ("target_ref", "refs/gwr/other"),
        ("result_commit", "89abcdef0123456789abcdef0123456789abcdef"),
    ],
)
def test_subject_component_mismatch_refuses(field: str, value: str) -> None:
    kwargs: dict[str, object] = {
        "supplied_subject": SUBJECT,
        "repository_id": RepositoryId(REPOSITORY_ID),
        "target_ref": TARGET_REF,
        "result_commit": RESULT_COMMIT,
    }
    kwargs[field] = RepositoryId(value) if field == "repository_id" else value

    with pytest.raises(RefContinuityBindingError, match="subject mismatch"):
        bind_ref_continuity_subject(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "provenance",
    [
        {"attempt_id": "../attempt", "dossier_version": 4, "digest": PREPARED_DIGEST},
        {"attempt_id": ATTEMPT_ID, "dossier_version": -1, "digest": PREPARED_DIGEST},
        {"attempt_id": ATTEMPT_ID, "dossier_version": 4, "digest": "abc"},
    ],
)
def test_docket_provenance_is_strict_and_never_part_of_subject(
    provenance: dict[str, object],
) -> None:
    with pytest.raises(RefContinuityBindingError):
        DocketProvenance(
            attempt_id=str(provenance["attempt_id"]),
            dossier_version=int(provenance["dossier_version"]),
            prepared_attempt_digest=str(provenance["digest"]),
        )


def test_pure_builder_calls_no_subprocess_and_preserves_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the ref-continuity builder must not spawn a subprocess")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    binding, observe = build_ref_continuity_observe_request(_request())

    assert binding.subject == SUBJECT
    assert observe.scope == SUBJECT
    assert observe.kind == "hypothesis"
    assert observe.basis == "import"
    assert observe.authoring_tier == "runtime_authored"
    assert observe.content["repository_id"] == REPOSITORY_ID
    assert observe.content["docket_provenance"] == {
        "system": "docket",
        "dossier_format": "gwr:attempt-dossier:v3",
        "attempt_id": ATTEMPT_ID,
        "dossier_version": 4,
        "prepared_attempt_digest": PREPARED_DIGEST,
    }
    assert ATTEMPT_ID not in observe.scope
    assert PREPARED_DIGEST not in observe.scope
    nonclaims = observe.content["does_not_establish"]
    assert isinstance(nonclaims, list)
    assert any("inspected Git" in line for line in nonclaims)
    assert any("NQ claim or disposition" in line for line in nonclaims)


def test_logical_subject_is_stable_across_path_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_dir = tmp_path / "first-clone"
    second_dir = tmp_path / "relocated-clone"
    first_dir.mkdir()
    second_dir.mkdir()

    monkeypatch.chdir(first_dir)
    first = observe_ref_continuity(_store(tmp_path / "first.db"), _request())
    monkeypatch.chdir(second_dir)
    second = observe_ref_continuity(_store(tmp_path / "second.db"), _request())

    assert first.subject == SUBJECT
    assert second.subject == SUBJECT
    assert first.observation.memory.scope == second.observation.memory.scope
    assert first.observation.memory.content == second.observation.memory.content
    assert str(first.binding.repository_id) == str(second.binding.repository_id)
    assert str(first.binding.repository_id) not in {
        str(first_dir),
        str(second_dir),
    }


def test_operation_creates_only_an_ordinary_observation_then_uses_existing_lifecycle(
    store: SQLiteStore,
) -> None:
    result = observe_ref_continuity(store, _request())
    memory = result.observation.memory

    assert result.subject == SUBJECT
    assert memory.status == MemoryStatus.OBSERVED
    assert memory.reliance_class == RelianceClass.NONE
    assert store.explain_memory(memory.memory_id).rely_ok is False

    committed = store.commit_memory(CommitMemoryRequest(
        memory_id=memory.memory_id,
        reliance_class=RelianceClass.ADVISORY,
    ))
    assert committed.memory.status == MemoryStatus.COMMITTED
    assert store.explain_memory(memory.memory_id).rely_ok is True

    original_content = dict(committed.memory.content)
    revoked = store.revoke_memory(RevokeMemoryRequest(
        memory_id=memory.memory_id,
        reason="the named ref no longer incorporates the result commit",
    ))
    assert revoked.memory.status == MemoryStatus.REVOKED
    assert revoked.memory.content == original_content
    assert store.explain_memory(memory.memory_id).rely_ok is False


def test_idempotency_cannot_silently_rebind_a_subject(store: SQLiteStore) -> None:
    first = observe_ref_continuity(
        store,
        _request(idempotency_key="docket-ref-continuity:one"),
    )
    replay = observe_ref_continuity(
        store,
        _request(idempotency_key="docket-ref-continuity:one"),
    )
    assert replay.observation.memory.memory_id == first.observation.memory.memory_id

    other_commit = "89abcdef0123456789abcdef0123456789abcdef"
    other_subject = (
        f"gwr:ref-continuity:v0:{REPOSITORY_ID}"
        f"#{TARGET_REF}@{other_commit}"
    )
    with pytest.raises(RefContinuityBindingError, match="does not exactly match"):
        observe_ref_continuity(
            store,
            _request(
                subject=other_subject,
                result_commit=other_commit,
                idempotency_key="docket-ref-continuity:one",
            ),
        )


def test_supported_cli_echoes_binding_and_leaves_memory_observed(
    tmp_path: Path,
) -> None:
    db = tmp_path / "continuity.db"
    stdout, stderr, code = _run_cli(db, _cli_args())

    assert code == 0, stderr
    result = json.loads(stdout)
    assert result["subject_contract"] == REF_CONTINUITY_CONTRACT
    assert result["subject"] == SUBJECT
    assert result["repository_id"] == REPOSITORY_ID
    assert result["target_ref"] == TARGET_REF
    assert result["result_commit"] == RESULT_COMMIT
    assert result["status"] == "observed"
    assert result["reliance_class"] == "none"
    assert result["authoring_tier"] == "runtime_authored"

    store = _store(db)
    memory = store.get_memory(result["memory_id"])
    assert memory.scope == SUBJECT
    assert memory.status == MemoryStatus.OBSERVED
    assert memory.reliance_class == RelianceClass.NONE


def test_exact_subject_flows_through_existing_commit_and_rely_export(
    tmp_path: Path,
) -> None:
    db = tmp_path / "continuity.db"
    observed_out, stderr, code = _run_cli(db, _cli_args())
    assert code == 0, stderr
    memory_id = json.loads(observed_out)["memory_id"]

    _out, stderr, code = _run_cli(
        db,
        ["commit", memory_id, "--reliance-class", "advisory"],
    )
    assert code == 0, stderr
    export_out, stderr, code = _run_cli(
        db,
        [
            "rely-export",
            memory_id,
            "--evaluation-time",
            "2026-07-26T12:00:00Z",
        ],
    )
    assert code == 0, stderr
    export = json.loads(export_out)
    assert export["subject"]["scope"] == SUBJECT
    assert export["rely"]["rely_ok"] is True
    assert export["rely"]["code"] == "eligible"


def test_supported_cli_rejects_path_as_identity_without_observing(
    tmp_path: Path,
) -> None:
    db = tmp_path / "continuity.db"
    stdout, stderr, code = _run_cli(
        db,
        _cli_args(repository_id=str(tmp_path / "checkout")),
    )

    assert code == 1
    assert stdout == ""
    assert "not a filesystem path" in stderr
    assert _store(db).query_memory(QueryMemoryRequest()).total == 0
