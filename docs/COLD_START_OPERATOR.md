# Continuity cold-start operator guide

This guide installs Continuity from a fresh source checkout and exercises the
supported Docket ref-continuity lifecycle against an explicitly selected,
empty state directory. It does not require a preinstalled `contctl`, a
developer shell alias, an existing Continuity database, or knowledge of the
source tree beyond its checkout root.

Continuity does not declare a published package or release in this guide.
Acquiring the authorized source checkout is a separate repository-access
step; the commands below install that checkout without inventing a packaging
or release policy.

## Prerequisites

- Python 3.11 or newer, including `venv` and `pip`;
- access to an approved Python package index or mirror for the dependencies
  declared in `pyproject.toml`;
- a fresh Continuity source checkout;
- a POSIX-compatible shell for the command spelling below.

The runtime dependency is `pydantic`. The optional `dev` extra installs
`pytest` and `pytest-timeout` for repository-native tests. No Git executable
is needed by `observe-ref-continuity`: that command validates caller-supplied
strings and does not inspect a checkout.

## Install without inheriting a developer environment

Start outside any pre-existing Continuity virtual environment. Set
`CONTINUITY_SOURCE` to the fresh checkout, then create all runtime state in a
new temporary directory:

```bash
CONTINUITY_SOURCE=/absolute/path/to/fresh/continuity
CONTINUITY_RUN_STATE="$(mktemp -d)"

python3 -m venv "$CONTINUITY_RUN_STATE/venv"
"$CONTINUITY_RUN_STATE/venv/bin/python" -m pip install \
  -e "$CONTINUITY_SOURCE[dev]"

CONTINUITY_PYTHON="$CONTINUITY_RUN_STATE/venv/bin/python"
CONTINUITY_CLI="$CONTINUITY_RUN_STATE/venv/bin/contctl"
CONTINUITY_STATE_DB="$CONTINUITY_RUN_STATE/state/continuity.db"

"$CONTINUITY_CLI" --help
"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" init
```

Using the virtual-environment executable directly proves which installation
is running. Supplying `--db` on every command makes the state location
explicit and takes precedence over `CONTINUITY_DB_PATH`,
`CONTINUITY_WORKSPACE`, Git-root discovery, and the user-home fallback. The
CLI creates the database's parent directory.

`CONTINUITY_DB_PATH=/some/path.db` is the supported environment-variable
alternative. `CONTINUITY_DB` is not an alias.

## Bind the Docket-owned subject

Docket must supply all of these values from its persisted dossier:

```bash
REPOSITORY_ID=repo-11111111111111111111111111111111
TARGET_REF=refs/gwr/target
RESULT_COMMIT=0123456789abcdef0123456789abcdef01234567
SUBJECT="gwr:ref-continuity:v0:${REPOSITORY_ID}#${TARGET_REF}@${RESULT_COMMIT}"

DOCKET_ATTEMPT=att-22222222222222222222222222222222
DOSSIER_VERSION=4
PREPARED_ATTEMPT_DIGEST=abababababababababababababababababababababababababababababababab
```

The literal values above are examples of the wire shapes, not identities to
reuse. Do not derive `REPOSITORY_ID` from a path, remote, checkout, commit, or
tree. Do not reconstruct `SUBJECT` when Docket has already returned the
complete subject; pass Docket's value and its components so Continuity can
check exact equality.

Record the binding:

```bash
OBSERVED_JSON="$CONTINUITY_RUN_STATE/observed.json"

"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  observe-ref-continuity \
  --subject "$SUBJECT" \
  --repository-id "$REPOSITORY_ID" \
  --target-ref "$TARGET_REF" \
  --result-commit "$RESULT_COMMIT" \
  --docket-attempt "$DOCKET_ATTEMPT" \
  --dossier-version "$DOSSIER_VERSION" \
  --prepared-attempt-digest "$PREPARED_ATTEMPT_DIGEST" \
  --idempotency-key "cold-start-observe" \
  > "$OBSERVED_JSON"

MEMORY_ID="$(
  "$CONTINUITY_PYTHON" -c \
    'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["memory_id"])' \
    "$OBSERVED_JSON"
)"
```

The JSON must echo the exact subject, repository ID, ref, and commit. Its
initial `status` is `observed` and its `reliance_class` is `none`. This step
does not inspect Git, establish ancestry, commit the memory, produce an NQ
verdict, or authorize action.

Relocating the governed repository does not change these logical inputs.
Docket updates its path locator while retaining its persisted
`RepositoryId`; Continuity continues to receive the same logical identity.
The Continuity source checkout and database paths are operational locators,
not components of the governed subject.

## Establish and export current reliance

Promotion uses the ordinary Continuity lifecycle:

```bash
"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  commit "$MEMORY_ID" \
  --reliance-class advisory \
  --idempotency-key "cold-start-commit"

EVALUATION_TIME=2026-07-27T12:00:00Z

"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  rely-export "$MEMORY_ID" \
  --evaluation-time "$EVALUATION_TIME" \
  > "$CONTINUITY_RUN_STATE/rely-positive-a.json"

"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  rely-export "$MEMORY_ID" \
  --evaluation-time "$EVALUATION_TIME" \
  > "$CONTINUITY_RUN_STATE/rely-positive-b.json"
```

For a committed, unexpired memory with intact premises, `rely.rely_ok` is
`true` and `rely.code` is `eligible`. The same store state at the same
evaluation time produces the same `export_id`; `exported_at` records each
invocation and is intentionally excluded from that identity. Compare the
machine identity rather than requiring the two complete JSON files to be
byte-identical:

```bash
"$CONTINUITY_PYTHON" -c '
import json, sys
with open(sys.argv[1], encoding="utf-8") as left:
    a = json.load(left)
with open(sys.argv[2], encoding="utf-8") as right:
    b = json.load(right)
assert a["export_id"] == b["export_id"]
print(a["export_id"])
' \
  "$CONTINUITY_RUN_STATE/rely-positive-a.json" \
  "$CONTINUITY_RUN_STATE/rely-positive-b.json"
```

The resulting `continuity.rely_export.v0` document is the supported input to
NQ's `nq-monitor witness continuity-record` surface. Follow NQ's own checked-in
help for its flags. Continuity does not own or reproduce NQ's import,
supporting-subject fence, reliance, or disposition semantics.

## Record later continuity loss

First establish through the repository owner or another authorized observer
that the named ref no longer incorporates the bound result commit. Continuity
does not inspect Git and must not manufacture that observation from its own
database. Once that external fact has actually changed, revoke the same memory
and export a later snapshot:

```bash
"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  revoke "$MEMORY_ID" \
  --reason "the named ref no longer incorporates the result commit" \
  --idempotency-key "cold-start-revoke"

"$CONTINUITY_CLI" --db "$CONTINUITY_STATE_DB" \
  rely-export "$MEMORY_ID" \
  --evaluation-time 2026-07-27T12:05:00Z \
  > "$CONTINUITY_RUN_STATE/rely-revoked.json"
```

The later export remains a valid record, but `rely.rely_ok` is `false`,
`rely.code` is `status_not_committed`, and `rely.details.status` is
`revoked`. The earlier export remains unchanged historical testimony.

## Keep negative conditions distinct

The supported surfaces preserve these operational distinctions:

| Condition | Observable result |
|---|---|
| Continuity established | `rely-export` record with `rely_ok=true`, code `eligible` |
| Continuity later lost | later `rely-export` record with `rely_ok=false` and a specific refusal code/detail |
| Continuity rely refusal | still a complete `rely-export` record and exit 0; refusal is evidence, not silence |
| No Continuity record | no export is produced and the CLI exits nonzero |
| NQ supporting evidence missing | an NQ-side result; it is not rewritten as a Continuity or Nightshift no-response |
| Nightshift no response | a Nightshift-side condition; it is not inferred from missing NQ supporting testimony |

NQ and Nightshift own the final two rows. Continuity's export supplies
testimony only.

## Repository-native focused gates

From the fresh source checkout:

```bash
cd "$CONTINUITY_SOURCE"
"$CONTINUITY_PYTHON" -m pytest \
  tests/test_ref_continuity.py \
  tests/test_rely_export.py
```

Each repeat of the operator journey should allocate a new
`CONTINUITY_RUN_STATE`. That prevents pre-existing databases, receipts,
fixtures, environment-selected stores, and prior lifecycle state from
affecting the result.
