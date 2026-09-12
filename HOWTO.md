# Continuity: local first run

This guide exercises Continuity itself. It does not run NQ, Nightshift, Docket,
or an external provider.

Requirements: Python 3.11 or newer and a clean source checkout.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest tests/ -v

RUN_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/constellation-continuity.XXXXXX")"
DB="$RUN_ROOT/continuity.db"
.venv/bin/contctl --db "$DB" init
.venv/bin/contctl --db "$DB" observe --scope tutorial --kind decision \
  --basis operator_assertion --content '{"choice":"keep-the-boundary-small"}' --receipt
```

Use the returned memory identifier with `explain`, then explicitly `commit`
before relying on it. This is local lifecycle and receipt evidence only; it
does not establish that the remembered content is true or authorize an effect.
The fresh directory is intentionally retained for inspection; remove that exact
directory when its local evidence is no longer needed.

Public source: <https://github.com/unpingable/constellation-continuity>

Verification note: the `--db`, `init`, and `observe` arguments above are
checked against `src/continuity/cli.py`. The prescribed test command is
`PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest tests/ -v`.
On 2026-09-12, the existing local `.venv` was initially stale after relocation:
its wrapper and editable package path referenced the old checkout. Those
metadata files were retained before a supported local editable reinstall
repaired the environment. A fresh environment created with the commands above
completed the isolated `init` and `observe --receipt` fixture successfully.
After the bounded repository-directory fixture expectation was updated for the
approved `constellation-continuity` root, the full suite passed: 375 tests in
17.28 seconds. These are local source and fixture checks, not a deployment or
external-authority claim.
