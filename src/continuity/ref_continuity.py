"""Docket -> Continuity binding for the Git ref-continuity subject.

This module implements the ratified, Git-specific subject contract::

    gwr:ref-continuity:v0:<repository_id>#<target_ref>@<result_commit>

The repository id is an opaque, Docket-owned identity.  Continuity receives
the complete subject and all of its components, checks their exact binding,
and records the supplied subject as an ordinary observed memory.  It never
discovers a repository, reads Git metadata, derives identity from a locator,
or commits the memory.

The pure :func:`build_ref_continuity_observe_request` function is the library
contract.  :func:`observe_ref_continuity` is the deliberately thin adapter to
the existing ``observe_memory`` operation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from continuity.api.models import (
    ActorRef,
    AuthoringTier,
    Basis,
    MemoryKind,
    MemoryStatus,
    ObserveMemoryRequest,
    ObserveMemoryResponse,
    RelianceClass,
    SourceRef,
)


REF_CONTINUITY_PREFIX = "gwr:ref-continuity:v0:"
REF_CONTINUITY_CONTRACT = "gwr:ref-continuity:v0"

_REPOSITORY_ID_RE = re.compile(r"repo-[0-9a-f]{32}\Z")
_FULL_COMMIT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_DOSSIER_FORMAT_RE = re.compile(r"gwr:attempt-dossier:v[0-9]+\Z")
_ATTEMPT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}\Z")

_LOCATOR_PREFIXES = (
    "/",
    "./",
    "../",
    "~",
    "file:",
    "git:",
    "http:",
    "https:",
    "ssh:",
)


class RefContinuityBindingError(ValueError):
    """The supplied subject or one of its exact components is invalid."""


@dataclass(frozen=True, slots=True)
class RepositoryId:
    """Opaque Docket-owned repository identity accepted by Continuity.

    Continuity does not mint this type and cannot reconstruct one from a path,
    remote, checkout, or Git object.  The narrow wire form mirrors Docket's
    typed ``RepositoryId`` and makes accidental locator-as-identity use fail
    closed.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise RefContinuityBindingError("repository_id must be a string")
        value = self.value
        lowered = value.lower()
        if (
            value != value.strip()
            or any(value.startswith(prefix) for prefix in _LOCATOR_PREFIXES)
            or "/" in value
            or "\\" in value
            or "://" in value
            or lowered.startswith("git@")
        ):
            raise RefContinuityBindingError(
                "repository_id must be an opaque Docket RepositoryId, not a "
                "filesystem path, URL, remote, or checkout locator"
            )
        if _REPOSITORY_ID_RE.fullmatch(value) is None:
            raise RefContinuityBindingError(
                "repository_id must match the opaque Docket wire form "
                "'repo-' followed by 32 lowercase hexadecimal characters"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class DocketProvenance:
    """Docket references attached as provenance, never subject identity."""

    attempt_id: str
    dossier_version: int
    prepared_attempt_digest: str
    dossier_format: str = "gwr:attempt-dossier:v3"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.attempt_id, str)
            or _ATTEMPT_ID_RE.fullmatch(self.attempt_id) is None
        ):
            raise RefContinuityBindingError(
                "docket attempt_id must be a non-empty opaque identifier, not a locator"
            )
        if isinstance(self.dossier_version, bool) or not isinstance(
            self.dossier_version, int
        ):
            raise RefContinuityBindingError("dossier_version must be an integer")
        if self.dossier_version < 0:
            raise RefContinuityBindingError("dossier_version must be non-negative")
        if (
            not isinstance(self.prepared_attempt_digest, str)
            or _SHA256_RE.fullmatch(self.prepared_attempt_digest) is None
        ):
            raise RefContinuityBindingError(
                "prepared_attempt_digest must be exactly 64 lowercase hexadecimal "
                "characters"
            )
        if (
            not isinstance(self.dossier_format, str)
            or _DOSSIER_FORMAT_RE.fullmatch(self.dossier_format) is None
        ):
            raise RefContinuityBindingError(
                "dossier_format must match 'gwr:attempt-dossier:vN'"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "system": "docket",
            "dossier_format": self.dossier_format,
            "attempt_id": self.attempt_id,
            "dossier_version": self.dossier_version,
            "prepared_attempt_digest": self.prepared_attempt_digest,
        }


@dataclass(frozen=True, slots=True)
class RefContinuityObservationRequest:
    """All caller-supplied inputs to one ordinary Continuity observation."""

    subject: str
    repository_id: RepositoryId
    target_ref: str
    result_commit: str
    docket: DocketProvenance
    actor: ActorRef | None = None
    source_observed_at: datetime | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class RefContinuityBinding:
    """The validated exact binding returned by the pure operation."""

    subject: str
    repository_id: RepositoryId
    target_ref: str
    result_commit: str

    def as_dict(self) -> dict[str, str]:
        return {
            "subject": self.subject,
            "repository_id": str(self.repository_id),
            "target_ref": self.target_ref,
            "result_commit": self.result_commit,
        }


@dataclass(frozen=True, slots=True)
class RefContinuityObservationResponse:
    """Validated binding plus the existing observed-memory response."""

    binding: RefContinuityBinding
    docket: DocketProvenance
    observation: ObserveMemoryResponse

    @property
    def subject(self) -> str:
        return self.binding.subject


class MemoryObserver(Protocol):
    """The existing store seam needed by :func:`observe_ref_continuity`."""

    def observe_memory(self, req: ObserveMemoryRequest) -> ObserveMemoryResponse: ...


def _validate_target_ref(target_ref: str) -> None:
    """Validate one exact, fully qualified Git ref name without invoking Git."""

    if not isinstance(target_ref, str):
        raise RefContinuityBindingError("target_ref must be a string")
    if target_ref != target_ref.strip() or not target_ref.startswith("refs/"):
        raise RefContinuityBindingError(
            "target_ref must be an exact fully qualified ref beginning with 'refs/'"
        )
    if target_ref == "refs/" or target_ref.endswith("/") or "//" in target_ref:
        raise RefContinuityBindingError("target_ref is not a complete Git ref")
    if any(ord(char) < 32 or ord(char) == 127 for char in target_ref):
        raise RefContinuityBindingError("target_ref contains a control character")
    if any(char in " ~^:?*[\\" for char in target_ref):
        raise RefContinuityBindingError("target_ref contains a forbidden Git ref character")
    if ".." in target_ref or "@{" in target_ref:
        raise RefContinuityBindingError("target_ref contains a forbidden Git ref sequence")
    components = target_ref.split("/")
    if any(
        component in {"", ".", ".."}
        or component.startswith(".")
        or component.endswith(".")
        or component.endswith(".lock")
        for component in components
    ):
        raise RefContinuityBindingError("target_ref contains a forbidden Git ref component")


def _validate_result_commit(result_commit: str) -> None:
    if not isinstance(result_commit, str) or _FULL_COMMIT_RE.fullmatch(
        result_commit
    ) is None:
        raise RefContinuityBindingError(
            "result_commit must be an exact full 40- or 64-character lowercase "
            "hexadecimal Git object id"
        )


def bind_ref_continuity_subject(
    *,
    supplied_subject: str,
    repository_id: RepositoryId,
    target_ref: str,
    result_commit: str,
) -> RefContinuityBinding:
    """Purely validate and return the exact caller-supplied subject binding.

    No field is normalized.  In particular, repository identity is not
    discovered or derived: callers must supply an already typed
    :class:`RepositoryId`.
    """

    if not isinstance(repository_id, RepositoryId):
        raise RefContinuityBindingError(
            "repository_id must be a pre-existing typed RepositoryId"
        )
    _validate_target_ref(target_ref)
    _validate_result_commit(result_commit)
    expected = (
        f"{REF_CONTINUITY_PREFIX}{repository_id}"
        f"#{target_ref}@{result_commit}"
    )
    if supplied_subject != expected:
        raise RefContinuityBindingError(
            "subject mismatch: supplied subject does not exactly bind the supplied "
            "repository_id, target_ref, and result_commit"
        )
    if len(supplied_subject) > 255:
        raise RefContinuityBindingError(
            "subject exceeds Continuity's 255-character scope limit"
        )
    return RefContinuityBinding(
        subject=supplied_subject,
        repository_id=repository_id,
        target_ref=target_ref,
        result_commit=result_commit,
    )


def build_ref_continuity_observe_request(
    req: RefContinuityObservationRequest,
) -> tuple[RefContinuityBinding, ObserveMemoryRequest]:
    """Build the ordinary observed-memory request for the supplied binding.

    This is the pure supported library operation.  It performs no I/O, consults
    no ambient checkout, and calls no clock.  Docket provenance is attached to
    the memory, but is never folded into the subject.
    """

    binding = bind_ref_continuity_subject(
        supplied_subject=req.subject,
        repository_id=req.repository_id,
        target_ref=req.target_ref,
        result_commit=req.result_commit,
    )
    docket = req.docket.as_dict()
    content: dict[str, object] = {
        "subject_contract": REF_CONTINUITY_CONTRACT,
        **binding.as_dict(),
        "assumption": (
            "the named result commit remains incorporated in the named "
            "repository ref's lineage"
        ),
        "docket_provenance": docket,
        "establishes": (
            "Continuity received and exactly bound this supplied logical subject "
            "as an observed working assumption"
        ),
        "does_not_establish": [
            (
                "that Continuity derived repository identity from a path, remote, "
                "checkout, commit, or tree"
            ),
            (
                "that Continuity inspected Git or independently established that "
                "the named ref currently incorporates the named commit"
            ),
            (
                "that the Docket attempt settled, that its evidence is true, or "
                "that its provenance confers custody"
            ),
            (
                "an NQ claim or disposition, admissibility, authority, reliance, "
                "or permission to act"
            ),
        ],
    }
    observe = ObserveMemoryRequest(
        scope=binding.subject,
        kind=MemoryKind.HYPOTHESIS,
        basis=Basis.IMPORT,
        content=content,
        source_refs=[
            SourceRef(
                kind="docket_attempt_dossier",
                ref=(
                    f"{req.docket.attempt_id}"
                    f"@v{req.docket.dossier_version}"
                ),
                note=(
                    f"{req.docket.dossier_format}; "
                    f"prepared_attempt_digest={req.docket.prepared_attempt_digest}"
                ),
            )
        ],
        confidence=0.5,
        source_observed_at=req.source_observed_at,
        actor=req.actor,
        authoring_tier=AuthoringTier.RUNTIME_AUTHORED,
        idempotency_key=req.idempotency_key,
    )
    return binding, observe


def observe_ref_continuity(
    observer: MemoryObserver,
    req: RefContinuityObservationRequest,
) -> RefContinuityObservationResponse:
    """Create one ordinary observed memory through the existing store seam."""

    binding, observe_req = build_ref_continuity_observe_request(req)
    response = observer.observe_memory(observe_req)
    memory = response.memory

    # The existing idempotency seam returns the first observation for a reused
    # key.  Re-check the complete result so a reused key cannot silently bind a
    # different subject or provenance.
    if (
        memory.scope != binding.subject
        or memory.kind != MemoryKind.HYPOTHESIS
        or memory.basis != Basis.IMPORT
        or memory.status != MemoryStatus.OBSERVED
        or memory.reliance_class != RelianceClass.NONE
        or memory.content != observe_req.content
        or memory.source_refs != observe_req.source_refs
    ):
        raise RefContinuityBindingError(
            "the observed memory does not exactly match the supplied "
            "ref-continuity binding and Docket provenance"
        )

    return RefContinuityObservationResponse(
        binding=binding,
        docket=req.docket,
        observation=response,
    )


__all__ = [
    "DocketProvenance",
    "REF_CONTINUITY_CONTRACT",
    "REF_CONTINUITY_PREFIX",
    "RefContinuityBinding",
    "RefContinuityBindingError",
    "RefContinuityObservationRequest",
    "RefContinuityObservationResponse",
    "RepositoryId",
    "bind_ref_continuity_subject",
    "build_ref_continuity_observe_request",
    "observe_ref_continuity",
]
