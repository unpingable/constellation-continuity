# Retired: WLP persistence adapter

**Status: RETIRED 2026-09-20. Do not implement.**

Continuity previously included a library-only adapter for retaining WLP
artifacts. Repository-wide caller inspection found no current consumer, and WLP
is no longer an active Constellation protocol. The adapter, its fixtures, and
its tests have therefore been removed from the current product tree.

This retirement does not change Continuity's supported persistence model:

- storage and retrieval do not establish truth or authority;
- a retained receipt does not decide whether a caller may rely on it;
- protocol-specific validation belongs to the protocol owner or caller;
- any future adapter requires a named current consumer, a versioned artifact
  contract, and independently grounded conformance fixtures.

No WLP maintenance, migration, transport, or compatibility commitment remains.
Historical repository revisions preserve the former implementation record.
