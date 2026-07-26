# `continuity.rely_export.v0` — the rely-result export

The machine-readable record Continuity owns for external testimony
consumers: **one memory's rely verdict at one explicit evaluation time.**
Produced by:

```
contctl rely-export <memory_id> [--evaluation-time ISO] [--repo R] [--commit C]
```

stdout carries exactly one JSON document; diagnostics go to stderr. Exit 0
means a record was produced — **a rely refusal is a valid export** (refusal
is evidence, not silence); exit 1 means no record exists (memory not found,
unreadable store, incomplete response — never a partial record); exit 2 is a
usage/policy error.

## What it establishes — and does not

The record establishes exactly: *continuity's rely gate returned `<code>`
for this memory at this evaluation time, under the recorded premises and
authoring tier.* Every record carries mandatory `does_not_establish` lines:
it is not an NQ verdict, not admissibility, not execution authority; rely
advises, never authorizes; the answer is consumer-neutral and
evaluation-time-relative — **a later evaluation may supersede it without
rewriting it, and absence of a newer export is not evidence of continuity or
discontinuity**; tier/ceiling quotes confer nothing. The declaration
export's forbidden-authority-key self-check is enforced on every record.

## Shape

`schema`, `export_id`, `exported_at`, `source` (store identity + exporter
provenance), `subject` (`memory_id`, `scope` — the operator-declared subject
binding, quoted not verified — `kind`, `basis`), `content_hash` (portable
content identity, Continuity's own digest domain), `status`/`supersedes`/
`revoked_by`, `authoring_tier`/`reliance_class`/`effective_reliance`
(copied, never upgraded), `lifecycle` (observe/commit event ids + per-store
receipt-chain hashes, opaque references), `times` (each timestamp its own
clock), `evaluation_time` (**the snapshot axis**), `rely` (the `RelyState`
verbatim — the closed seven-code vocabulary; `hard_premise_unavailable`
details keep `:missing` distinct from `:revoked`, and
`status_not_committed` keeps `details.status`, so cannot-establish is never
collapsed into discontinuity), `premises`, `history`, `establishes`,
`does_not_establish`.

## Determinism and identity

`export_id = sha256(canonical_json(record minus export_id/exported_at))` —
same store state at the same evaluation time yields the same id regardless
of when the export runs. A later evaluation is a **new** record with a new
identity; older records remain historical bytes, never rewritten.

## Consumer rules (what NQ's import profile enforces on its side)

Exact identity/version + same bytes → idempotent; same
(memory, evaluation_time) with a changed semantic core → substitution
refusal; later evaluation time → new immutable testimony; unsupported
schema or malformed record → typed refusal, no partial packet. NQ treats
`content_hash` and `export_id` opaquely and computes its own raw-byte
digest — digest domains stay separate.

## Golden vectors

`tests/fixtures/rely_export_vectors/` — six sanitized vectors (eligible,
premise-revoked discontinuity, uncommitted cannot-establish, revoked
discontinuity, runtime-authored tier, later snapshot), each internally
consistent (`export_id` recomputes; codes in the closed vocabulary; no
authority-shaped key). NQ verifies the same files independently
(`nq` repo, `crates/nq-monitor/tests/fixtures/continuity/vectors/`).

## Relation to NQ

NQ imports this record through `nq-monitor witness continuity-record` as an
external projection, evaluates the narrow `continuity_rely_eligible` claim
through its ordinary registry, and may require that claim as **supporting
evidence** in consumer-indexed reliance. Continuity emits no NQ
admissibility judgment and no execution authority; NQ re-runs none of
Continuity's trajectory law. The two `rely` verbs keep their different
subjects.
