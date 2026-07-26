"""Rely export — `continuity.rely_export.v0`, a per-memory rely-result snapshot.

The record Continuity OWNS for external testimony consumers (the NQ seam): one
memory's rely verdict at one explicit ``evaluation_time``, with subject
identity, lifecycle references, premises, and provenance — and nothing that
could read as an NQ verdict, admissibility, or execution authority.

What it says, and says only:

    here is the memory (id, scope, kind, basis) and its portable content hash;
    here is its lifecycle state and provenance (authoring tier, ceilings);
    here is what the rely gate answered at this evaluation time, verbatim;
    here are the premises the answer depended on;
    here is a deterministic digest over that core.

What it must NOT say: that anything is authoritative/current/canonical, that
any consumer may act, or that a later evaluation cannot supersede this one.
A rely **refusal is a valid export** — refusal is evidence, not silence — and
the refusal code is carried verbatim: ``hard_premise_unavailable`` details
keep their ``:missing`` (cannot-establish) vs ``:revoked`` (discontinuity)
distinction, and ``status_not_committed`` keeps ``details.status`` so
"never committed" is never collapsed into "revoked".

Determinism: ``export_id`` is a sha256 over the canonical record minus
``export_id`` and ``exported_at`` — same store state + same evaluation time
=> same id, regardless of when the export ran. The clock for ``exported_at``
is resolved at the boundary (the CLI), never here. A later evaluation is a
**new** record with a new identity; nothing rewrites an earlier one.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from pydantic import ConfigDict, Field

from continuity.api.models import ExplainMemoryResponse, JsonModel
from continuity.declaration_export import (
    FORBIDDEN_EXPORT_FIELDS,
    ExportError,
    ExportSource,
)
from continuity.util.clock import to_isoformat
from continuity.util.hashing import content_hash
from continuity.util.jsoncanon import canonical_json

SCHEMA = "continuity.rely_export.v0"

#: The one establishes-sentence template. The export establishes what the rely
#: gate answered — never what any consumer may do with the answer.
_ESTABLISHES = (
    "continuity's rely gate returned {code} for memory {memory_id} at "
    "{evaluation_time} under the recorded premises and authoring tier"
)

#: Stamped on every record, whatever the verdict. These are the office
#: boundary, stated on the artifact itself.
MANDATORY_DOES_NOT_ESTABLISH = (
    "this record is a continuity rely snapshot at the stated evaluation time; "
    "it is not an nq verdict, not admissibility, and not execution authority",
    "rely advises, never authorizes; the answer is consumer-neutral and binds "
    "no consumer to anything",
    "a later evaluation may supersede this answer without rewriting it; "
    "absence of a newer export is not evidence of continuity or discontinuity",
    "authoring-tier and reliance-class ceilings quoted here are continuity "
    "law, carried for disclosure, and confer nothing",
)


class RelySnapshot(JsonModel):
    """The rely gate's answer, verbatim."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    rely_ok: bool
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SubjectRef(JsonModel):
    """The exported memory's identity. ``scope`` is Continuity's
    operator-declared subject binding — quoted, never verified here."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    memory_id: str
    scope: str
    kind: str
    basis: str


class LifecycleRefs(JsonModel):
    """Observation/commitment identities, where the event log records them.
    Receipt hashes are Continuity's own per-store chain hashes (bare hex by
    that chain's convention) — opaque references, not portable digests."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    observe_event_id: str | None = None
    observe_receipt_hash: str | None = None
    latest_commit_event_id: str | None = None
    latest_commit_receipt_hash: str | None = None


class PremiseEntry(JsonModel):
    """One premise link the rely answer could depend on."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    src: str
    relation: str
    strength: str
    status: str


class TimesBlock(JsonModel):
    """Each timestamp is its own clock; none impersonates another."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    created_at: str
    updated_at: str
    source_observed_at: str | None = None
    expires_at: str | None = None


class SourceBlock(JsonModel):
    """Which Continuity store produced this record."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    system: str = "continuity"
    store_id: str | None = None
    scope_kind: str | None = None
    schema_version: int | None = None
    exporter: ExportSource


class RelyExport(JsonModel):
    """A `continuity.rely_export.v0` document."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, use_enum_values=True)

    schema_id: str = Field(default=SCHEMA, serialization_alias="schema", validation_alias="schema")
    export_id: str
    exported_at: str
    source: SourceBlock
    subject: SubjectRef
    content_hash: str
    status: str
    supersedes: str | None = None
    revoked_by: str | None = None
    authoring_tier: str
    reliance_class: str
    effective_reliance: str
    lifecycle: LifecycleRefs
    times: TimesBlock
    evaluation_time: str
    rely: RelySnapshot
    premises: list[PremiseEntry]
    history: dict[str, int]
    establishes: list[str]
    does_not_establish: list[str]

    def canonical_dict(self) -> dict[str, Any]:
        """Wire form (the `schema` key by alias)."""
        return self.model_dump(mode="json", by_alias=True)


def _all_keys_lower(obj: object):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k).lower()
            yield from _all_keys_lower(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _all_keys_lower(item)


def _assert_no_forbidden_fields(export: RelyExport) -> None:
    hits = sorted(
        {k for k in _all_keys_lower(export.canonical_dict()) if k in FORBIDDEN_EXPORT_FIELDS}
    )
    if hits:
        raise ExportError(
            f"rely export carries forbidden authority field(s) {hits!r}; the "
            "export quotes a rely snapshot, it does not assert authority, "
            "recency, or supersession-as-truth"
        )


def compute_export_id(core: dict[str, Any]) -> str:
    """sha256 over the canonical record minus ``export_id``/``exported_at``."""
    body = {k: v for k, v in core.items() if k not in ("export_id", "exported_at")}
    return "sha256:" + sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _link_src(link: Any) -> str:
    if getattr(link, "src_memory_id", None):
        return str(link.src_memory_id)
    if getattr(link, "src_receipt_id", None):
        return f"receipt:{link.src_receipt_id}"
    src_ref = getattr(link, "src_ref", None)
    if src_ref is not None:
        kind = getattr(src_ref, "kind", "ref")
        ref = getattr(src_ref, "ref", "")
        return f"{kind}:{ref}"
    return "unknown"


def build_rely_export(
    explain: ExplainMemoryResponse,
    store_metadata: dict[str, Any] | None,
    *,
    exported_at: str,
    exporter: ExportSource,
) -> RelyExport:
    """Project one ``explain_memory`` response into a rely export. Pure: no
    clock, no store access — everything comes from the supplied response.

    Raises :class:`ExportError` when the response cannot yield a complete
    record (no partial record is ever emitted).
    """
    memory = explain.memory
    state = explain.rely_state
    if state is None:
        raise ExportError(
            "explain response carries no rely_state; a rely export cannot be "
            "produced without a rely evaluation"
        )
    if explain.evaluation_time is None:
        raise ExportError("explain response carries no evaluation_time")

    details = dict(state.details or {})
    authoring_tier = str(details.get("authoring_tier") or memory.authoring_tier)
    effective = details.get("effective_reliance")
    if effective is None:
        raise ExportError(
            "rely_state.details carries no effective_reliance; refusing to "
            "reconstruct a ceiling the gate did not state"
        )

    observe_event_id = None
    observe_receipt_id = None
    latest_commit_event_id = None
    latest_commit_receipt_id = None
    for event in explain.events:
        etype = str(event.event_type)
        if etype == "observe" and observe_event_id is None:
            observe_event_id = event.event_id
            observe_receipt_id = event.receipt_id
        if etype == "commit":
            latest_commit_event_id = event.event_id
            latest_commit_receipt_id = event.receipt_id
    receipt_hash_by_id = {r.receipt_id: r.hash for r in explain.receipts}

    meta = store_metadata or {}
    raw_schema_version = meta.get("schema_version")
    record = {
        "schema": SCHEMA,
        "export_id": "",
        "exported_at": exported_at,
        "source": SourceBlock(
            store_id=meta.get("store_id"),
            scope_kind=meta.get("scope_kind"),
            schema_version=int(raw_schema_version) if raw_schema_version is not None else None,
            exporter=exporter,
        ).model_dump(mode="json", by_alias=True),
        "subject": SubjectRef(
            memory_id=memory.memory_id,
            scope=str(memory.scope),
            kind=str(memory.kind),
            basis=str(memory.basis),
        ).model_dump(mode="json", by_alias=True),
        "content_hash": content_hash(memory),
        "status": str(memory.status),
        "supersedes": memory.supersedes,
        "revoked_by": memory.revoked_by,
        "authoring_tier": authoring_tier,
        "reliance_class": str(memory.reliance_class),
        "effective_reliance": str(effective),
        "lifecycle": LifecycleRefs(
            observe_event_id=observe_event_id,
            observe_receipt_hash=receipt_hash_by_id.get(observe_receipt_id),
            latest_commit_event_id=latest_commit_event_id,
            latest_commit_receipt_hash=receipt_hash_by_id.get(latest_commit_receipt_id),
        ).model_dump(mode="json", by_alias=True),
        "times": TimesBlock(
            created_at=to_isoformat(memory.created_at),
            updated_at=to_isoformat(memory.updated_at),
            source_observed_at=(
                to_isoformat(memory.source_observed_at)
                if memory.source_observed_at is not None
                else None
            ),
            expires_at=(
                to_isoformat(memory.expires_at) if memory.expires_at is not None else None
            ),
        ).model_dump(mode="json", by_alias=True),
        "evaluation_time": to_isoformat(explain.evaluation_time),
        "rely": RelySnapshot(
            rely_ok=state.rely_ok,
            code=str(state.code),
            message=state.message,
            details=details,
        ).model_dump(mode="json", by_alias=True),
        "premises": [
            PremiseEntry(
                src=_link_src(link),
                relation=str(link.relation),
                strength=str(link.strength),
                status=str(link.status),
            ).model_dump(mode="json", by_alias=True)
            for link in explain.premises
        ],
        "history": {
            "event_count": len(explain.events),
            "receipt_count": len(explain.receipts),
        },
        "establishes": [
            _ESTABLISHES.format(
                code=str(state.code),
                memory_id=memory.memory_id,
                evaluation_time=to_isoformat(explain.evaluation_time),
            )
        ],
        "does_not_establish": list(MANDATORY_DOES_NOT_ESTABLISH),
    }
    record["export_id"] = compute_export_id(record)
    export = RelyExport.model_validate(record)
    _assert_no_forbidden_fields(export)
    return export
