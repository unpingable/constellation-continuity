# constellation-continuity beta work

Planning only, recorded 2026-10-01. Work below is not started by publication of this plan. Source, package, installation, runtime and composition standing remain separate.

## Current state

Start from [`dev/operator-beta`](https://github.com/unpingable/constellation-continuity/tree/dev/operator-beta), canonical product reconciliation at `3da731ea7fbb91340b74005e8d3a8a1626ad6c9b`. Documentation commits after that point do not select a different product base or transfer predecessor qualification.

Current rely checks direct hard premises for missing or revoked status; premise expiry/transitive reliance are an unresolved documented scope decision.

## Scope and exclusions

This plan routes current requirements and evidence needed for future bounded work. It does not resume alpha qualification, launch providers, mutate a deployment or implement product changes. Target-specific configuration and operational facts belong in program/application records; component documentation describes abstract interfaces only.

`agent_gov`, Classic NQ (`nq-classic`), retired monorepos, predecessor product lines and historical application implementations are historical/migration evidence only. They are not forward source donors, dependencies or instructions to restore removed APIs. Retired WLP compatibility remains excluded. Record a current requirement if old evidence suggests missing functionality; require an explicit owner decision before any revival.

## CT-01: Decide Continuity hard-premise reliance scope

`COMPONENT_PRODUCT` · **Post-beta** · Project: Blocked.

Problem: Current query checks direct hard premises for missing/revoked status; transitive revocation and premise expiry are not traversed.

Intended outcome: Choose query-time recursive reliance with cycle protection or narrow the documented scope; retain explicit links and append-only history.

Scope/exclusions: No automatic cascades, inference from text or revival of predecessor reason-maintenance implementations.

Dependencies: Program release scope and current component contracts.

Acceptance/evidence: Revoked grand-premise, expired direct premise and cycle cases pin chosen behavior.

Owner decisions: Owner selects recursive scope or explicit direct-only contract.

Owning issue: [CT-01](https://github.com/unpingable/constellation-continuity/issues/1).
