# Bounded historical execution evidence salvage

Verdict: **SALVAGE_AND_GLUE_NOW**, by salvaging semantics and historical evidence,
not classic runtime code. Constellation Continuity already supplies the storage
model. The useful missing piece was a small content filter for finding it.

## Identity and liveness

- Continuity base: `ccf70cb3d2aae67fd64c4ddd3a6f924da415cca1`.
- Agent Gov classic source: `df61549a5e9a0dcc63ebe21efc90bd8958f64123`.
- Branch: `spike/agent-gov-evidence-3a78d91f`.
- Run: `3a78d91f-2d44-4c07-b420-4da62bc25f6a`, host `crow`.
- Shared registry: `/data/git`; completion notice at
  `.lanes/continuity-salvage/3a78d91f-2d44-4c07-b420-4da62bc25f6a/COMPLETE.json`.
  This notice is readiness for review, not acceptance. Exact result identity,
  test logs, specimen database/output, source hashes, and custody are in that run.

Classic's working-tree `AGENTS.md` explicitly deprecates it as of 2026-09-08.
Its preexisting edits to that file, README and .gitignore were not changed.
Continuity's manifest depends on Pydantic, not classic. Classic's
`src/governor/doctrine.py` still has an optional runtime import of Continuity;
this is doctrine consultation, not historical trajectory retrieval. No deployed
consumer is established by that import. Current Docket source has the distinct
`crates/gwr-core/src/ref_continuity.rs` subject constructor and a CLI binding;
Continuity's `ref_continuity.py` already records that narrow subject. Neither
needs replacement by classic concepts. This was a bounded source inspection,
not a whole-estate or deployment audit. WLP remains retired and untouched.

## 1. Salvage inventory

Paths in the first column are within the pinned classic repository. Implemented
code is distinguished from a current supported integration: these implementations
exist, but their existence does not establish new consumers or qualification.

| Component | Purpose | Reusable? | Destination in Continuity | Caveats |
|---|---|---|---|---|
| `src/governor/receipts.py`, `producers.py` | Command, file and changeset observations | Field semantics | Existing `content` and `SourceRef` | Exit status/output hashes describe an observation; not acceptance; bytes may be unavailable |
| `src/governor/gate_receipt.py` | Subject/evidence/policy-bound verdict and receipt role | Historical record only | Observed note + original source/hash | `pass` and `proceed` remain foreign reported values, never commit/authority |
| `libs/receipt_v1/src/receipt_v1/types.py` | Separate decision, execution status, result identity and effects confidence | Semantics, no code extraction needed | Ordinary content and explicit source/premise references | Permission is not execution; result is not independently accepted outcome |
| `libs/receipt_kernel/` | Hash-linked events, blobs and availability states | Semantics already substantially covered | Existing events, receipts, source refs | New store would duplicate Continuity; classic store declares a single writer; chain is not authorship proof |
| `src/governor/runtime/events.py` | Session/sequence/parent/receipt correlation | Preserve supplied identifiers as content | Existing notes/experiments and soft links | Do not import event bus, supervisor, lane grants or event emission machinery |
| `src/governor/context_manifest.py`, `provenance_labels.py` | Content-bound source regions and provenance labels | Preserve actual region/source hashes when available | Source refs and original content | Reserved signature fields are not evidence; capability metadata is not a grant |
| `src/governor/context_compact.py` | Retained/dropped content identities and summary bounds | Loss-accounting principle | Explicit excerpt truncation + full-record pointers | No summarizer import; character bound is not a tokenizer bound |
| `src/governor/evidence_store.py`, `libs/receipt_v1/.../store.py` | Claim/run/evidence lookups | Lookup semantics | Existing query/explain plus literal text filter | No semantic retrieval; classic JSONL limit does not bound corpus scanning |
| `src/governor/state_index_export.py` | Source-byte identities, observed vs declared status | Provenance semantics | Source refs/content | Shipped scanner is not the proposed future registry; do not import registry plans |
| `src/governor/cooked_context_orchestrator.py`, `work_container.py` | Parent/outcome correlation and bounded work projection | Semantics only | Preserve explicit context/parent refs when sourced | Orchestration, routing, admission, capability requirements and effects stay outside Continuity |
| CD2 review packet, verifier receipt, validation, later disposition | One actual intervention and later reported consequences | Yes: historical specimen | Four observed memories, three soft `about` edges | Receipt, review readiness and later landing are different assertions with different sources |

## 2. Existing overlap and conflicts

`MemoryObject` already has generic content, scope, kind, authoring tier, sources,
and observation/recording timestamps. `MemoryEvent` and `ReceiptRecord` record
mutations; `PremiseRef`/`MemoryLink` preserve explicit association and lineage.
`experiment`, `note`, `lesson`, and `summary` already cover this use. `get_case`
groups a scope, including revoked branches, but loads the whole scope and selects
only one summary. It is not a bounded trajectory replay API.

There is no need for a trajectory table, outcome enum, second receipt store,
new actor registry, or dependency on classic. In particular:

- Historical `status`, `verdict`, `authority`, and actor labels stay inside
  source content. They never set Continuity status, reliance, approval, or standing.
- The copier's `ActorRef` identifies the copier. It does not impersonate the
  historical executor. `runtime_authored` describes the deterministic copy.
- Memory recording time is not historical action time. The specimen keeps
  source timestamps verbatim in content; it does not guess `source_observed_at`.
- Soft `about` links say these documents concern the same specimen. They do not
  prove causation or independent acceptance. The packet content hash is pinned.
- Existing idempotency returns current memory for a reused key without comparing
  request content. The example binds keys to the whole translated request and
  checks the returned observation, refusing changed/revoked/promoted records.
- Existing `ref_continuity` and cross-store `import_memory` contracts remain
  unchanged. Foreign historical JSON is an observation, not a portable native
  memory eligible for an automatic commit/import-status mapping.

## 3. Minimal architecture and supported data

```text
four pinned historical files -> observe_memory (observed / none)
                            -> SourceRefs + soft about links
new task's literal phrase   -> query_memory(text, scope, kind, limit)
                            -> bounded evidence cards + original source pointers
                            -> supervising model interprets; acceptance owner decides
```

The only production changes are optional `QueryMemoryRequest.text`, its SQL
filter, CLI `query --text`, MCP `memory_query.text`, and source refs in MCP query
results. Existing calls without `text` retain their behavior. Matching is a
literal substring of stored content JSON (including keys), ASCII case-insensitive,
with no wildcard expansion or relevance score. It composes with scope, kind,
status, expiry, limit and offset filters. It may scan matching scope contents;
it is not an indexed semantic search engine or a snapshot across concurrent pages.
The API limits row count, not row bytes. The example separately bounds its cards.

Minimum useful record, using only supplied data:

| Requested information | Actual source / treatment |
|---|---|
| Task/campaign | Packet `lane`, `packet_id`, `playbook_id`; disposition `queue_id` |
| Classification | Existing playbook identity; no invented phenotype |
| Agent/model/role | Not reliably identified by these four records; left absent. Receipt `principal_id=local` is not a model identity |
| State/context seen | Packet `base_sha`, allowed/forbidden paths, design notes; verifier `git_sha`, `dirty`, `cwd` |
| Intervention/artifacts | Packet changes, tests, artifacts; verifier command/output hashes |
| Provenance | Pinned Git revision/path and SHA-256 of exact source bytes per memory |
| Time/order | Original receipt timestamp and disposition recorded_at retained; no invented total causal order |
| Acceptance/review | Literal validation `ready_for_operator_apply`, receipt `pass`, later disposition evidence; never conflated |
| Repair/rollback/abandonment | Not present in this specimen; no fabricated iteration or terminal state |
| Later consequences | Disposition's explicit receipt, validation and landing references; three associated evidence memories |

## 4. Implemented vertical slice

[`scripts/historical_trajectory.py`](../scripts/historical_trajectory.py) copies
four real CD2 records retained in
[`tests/fixtures/historical_cd2/`](../tests/fixtures/historical_cd2/manifest.json).
The manifest pins their source revision, paths and byte hashes. No classic
installation or fixture generator is needed. All source bytes are verified
before the first write. The four observations are individually transactional;
an interrupted run can repeat ingestion without duplicating completed records.
This is a source-checkout example, not a maintained classic-format adapter.

```bash
PYTHONPATH=src python -m scripts.historical_trajectory
# Temporary isolated store, removed on exit. For retained, inspectable evidence:
PYTHONPATH=src python -m scripts.historical_trajectory --db /tmp/cd2-history.db
PYTHONPATH=src python -m continuity.cli --db /tmp/cd2-history.db query \
  --scope case:historical-agent-gov-cd2 --kind experiment --text state-index --limit 3
```

A supervisor considering another state-index change can retrieve the CD2 packet:
it reports `proposed_patch` against base `a904f5b69fad385133c31f685b7e116bb344787b`.
The linked verifier reports exit 0 and `pass`; a separate validator reports ready
for operator apply; the later disposition reports landing `ca63a34`. These are
attributed historical statements, not a fresh revalidation or proof of causation.
The source output hashes and exact receipt ID remain in the stored record.

The example emits up to three matching packet cards, each with up to three
associated evidence cards and at most 1600 characters per excerpt. It reports
total matches, omitted associations and excerpt truncation, includes memory
status separately, and supplies source and memory/link identities for inspection.
It selects existing source fields for excerpts; full original JSON remains stored.
No-match and absent evidence stay unknown. Expiration defaults remain unchanged;
general historical queries can explicitly set `include_expired=True`.

Targeted qualification covers exact content/provenance round trip, attributed
outcome links, idempotent row/receipt counts, changed-source refusal before writes,
changed-observation refusal, absent evidence, disputed testimony, output bounds,
literal SQL-looking inputs, filter composition, pagination, CLI and MCP surfaces.
Full-suite results and immutable result identity are in the run receipt.

### Formalization consideration

Decision owner: supervising Codex for this spike; independent acceptance remains
separate. Proposition: for these pinned inputs, copying preserves source content
and refs, associates later evidence without granting reliance, and repeating the
same translation adds no observations/receipts. Search only filters existing
observations; neither missing evidence nor a foreign verdict changes status.
Source identities are above and in the fixture manifest; result identity is in
the completion/validation receipts.

Practical round-trip tests and deterministic negative controls suffice for this
finite mapping and read filter. No new concurrent protocol, authority transition,
or cross-language format is introduced, so no model is added. Explicit limits:
hashes do not prove historical truth; refs may not resolve outside the archive;
an excerpt can omit important context; sequential reads are not one concurrent
snapshot; `about` is not causality. Generalized multi-writer import or loss-aware
trajectory assembly would require a separately bounded proposition and review.

## 5. Explicitly rejected scope

No dispatch, model/agent selection, rankings/Elo, reputation/decay, optimization,
coalitions, voting, policy engine, scheduler changes, autonomous workflow mutation,
new service, live classic consumer, or speculative multi-agent architecture.
No new ontology, full-history summarizer, vector search, acceptance adjudicator,
or MapSkew implementation. No merges, pushes, deployments or migrations.

## 6. Verdict

**SALVAGE_AND_GLUE_NOW.** Continuity already covers storage and lineage; a small
query addition and an evidence example provide immediate value. Salvage the
separation of action, observation and later consequence. Importing classic code
would duplicate working machinery and preserve a retired integration obligation.
