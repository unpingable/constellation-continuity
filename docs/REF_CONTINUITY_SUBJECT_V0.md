# Docket ref-continuity subject contract

Continuity supports the ratified Git-specific subject:

```text
gwr:ref-continuity:v0:<repository_id>#<target_ref>@<result_commit>
```

It names one working assumption: that the exact result commit remains
incorporated in the exact governed ref's lineage for one opaque,
Docket-owned repository identity.

This is a subject-binding operation, not a Git probe. Docket supplies the
complete subject, the typed repository ID, the exact ref and full commit, and
the dossier provenance. Continuity validates that the supplied string binds
those components byte-for-byte and writes an ordinary `observed` memory. It
does not commit, revoke, or make the memory rely-eligible automatically.

## Repository identity

The accepted wire form is Docket's opaque typed `RepositoryId`:

```text
repo-11111111111111111111111111111111
```

Continuity never mints it and never reconstructs it. Filesystem paths, remote
URLs, checkout locations, commit IDs, tree IDs, and arbitrary repository
labels are rejected at this boundary. A path may still select an operational
Continuity database or locate a Docket checkout; it is not the logical
repository identity.

Continuity can validate the typed wire but cannot prove how an otherwise
well-formed ID was minted. Docket owns that provenance and must mint or
register the ID once in its persisted dossier/registry. This surface adds no
fallback that hashes or canonicalizes a path or remote.

## Supported CLI

```bash
contctl --db continuity.db observe-ref-continuity \
  --subject 'gwr:ref-continuity:v0:repo-11111111111111111111111111111111#refs/gwr/target@0123456789abcdef0123456789abcdef01234567' \
  --repository-id repo-11111111111111111111111111111111 \
  --target-ref refs/gwr/target \
  --result-commit 0123456789abcdef0123456789abcdef01234567 \
  --docket-attempt att-22222222222222222222222222222222 \
  --dossier-version 4 \
  --prepared-attempt-digest abababababababababababababababababababababababababababababababab
```

The machine JSON echoes the exact subject and components and identifies the
ordinary memory and observe receipt. Its initial posture is:

```json
{
  "subject_contract": "gwr:ref-continuity:v0",
  "subject": "gwr:ref-continuity:v0:repo-11111111111111111111111111111111#refs/gwr/target@0123456789abcdef0123456789abcdef01234567",
  "repository_id": "repo-11111111111111111111111111111111",
  "target_ref": "refs/gwr/target",
  "result_commit": "0123456789abcdef0123456789abcdef01234567",
  "status": "observed",
  "reliance_class": "none",
  "authoring_tier": "runtime_authored"
}
```

The Docket attempt, dossier version/format, and prepared-attempt digest are
persisted as provenance on the memory; they are never subject components.
`--idempotency-key` makes a retry return the first exact observation. Reusing
the key for a different subject or provenance refuses instead of rebinding it.

## Supported library face

`continuity.ref_continuity` exports:

- `RepositoryId` and `DocketProvenance`;
- `RefContinuityObservationRequest`;
- `bind_ref_continuity_subject`, the pure exact-binding check;
- `build_ref_continuity_observe_request`, the pure builder for the existing
  `ObserveMemoryRequest`;
- `observe_ref_continuity`, the thin adapter to an existing
  `observe_memory` store.

The pure functions perform no I/O, call no clock, inspect no checkout, and
spawn no process. The adapter does only the existing observed-memory write.
The existing `commit`, `revoke`, `explain`, and `rely-export` surfaces govern
the later trajectory unchanged.

## Exact validation and nonclaims

- Repository ID: `repo-` plus 32 lowercase hexadecimal characters.
- Target ref: a full valid `refs/...` name, preserved verbatim.
- Result commit: exactly 40 or 64 lowercase hexadecimal characters; no
  abbreviations or normalization.
- Subject: exact equality with the components above; any mismatch refuses.
- Prepared-attempt digest: exactly 64 lowercase hexadecimal characters.

The observation does not establish current Git ancestry, historical Docket
settlement, source truth, custody upgrade, NQ admissibility or disposition,
authority, reliance, or permission to act. It records only that Continuity
received and bound the exact supplied logical subject as an observed working
assumption.
