# Inspect and close a bounded work session

Continuity persists explicit observations, decisions, constraints, and their
premises. It does not understand a task, inspect a working tree, refresh a
source, or close work by itself. The caller supplies those facts and chooses
each lifecycle transition.

Use an explicit database when reproducing this example so the selected store
does not depend on the current directory:

```sh
RUN_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/continuity-session.XXXXXX")"
DB="$RUN_ROOT/continuity.sqlite"
contctl --db "$DB" init
contctl --db "$DB" where --json
```

First inspect existing state. `latest` is the read side of the documented
query-then-supersede convention:

```sh
contctl --db "$DB" latest --scope case:example --kind project_state
contctl --db "$DB" case case:example --json
```

An empty result is not permission to act. Record a directly captured source
state as observed, then explicitly commit it if it should be retrievable:

```sh
contctl --db "$DB" observe -q --scope case:example --kind project_state \
  --basis direct_capture \
  --content '{"handoff":"obsolete","source_revision":"v1"}'
contctl --db "$DB" commit MEMORY_ID --reliance-class retrieve_only
```

When the source changes, create another observation with the old memory's
identifier in `--supersedes`; do not rewrite the old object. Add hard premises
to a synthesized closeout so `explain` can surface later discontinuity:

```sh
contctl --db "$DB" observe -q --scope case:example --kind project_state \
  --basis direct_capture --supersedes OLD_MEMORY_ID \
  --source-observed-at 2026-09-12T12:00:00Z \
  --content '{"handoff":"elsewhere","source_revision":"v2","refreshed":true}'
contctl --db "$DB" commit REFRESHED_MEMORY_ID --reliance-class retrieve_only

contctl --db "$DB" observe -q --scope case:example --kind summary \
  --basis synthesis --content '{"status":"closed"}' \
  --premise DECISION_MEMORY_ID:depends_on:hard \
  --premise REFRESHED_MEMORY_ID:depends_on:hard
contctl --db "$DB" commit CLOSEOUT_MEMORY_ID --reliance-class advisory
contctl --db "$DB" explain CLOSEOUT_MEMORY_ID
```

The MCP server exposes the same lifecycle over stdio as `memory_observe`,
`memory_commit`, `memory_query_latest`, `memory_get_case`, and
`memory_explain`. Select its store explicitly with `continuity-mcp --db PATH`
or with the documented environment/workspace configuration. MCP tool
availability depends on the client configuration; installing this repository
does not make a tool available in every session.

There is no implemented session-start orientation hook or typed task-plus-CWD
packet. Current-directory handling selects a project-local database only when
no explicit database, environment database, or workspace was selected. The
proposed orientation mechanism is documented separately under `docs/gaps/` and
must not be described as implemented. Stored content, a receipt, or a positive
reliance result does not establish truth, comprehend the source, or authorize
an external action.
