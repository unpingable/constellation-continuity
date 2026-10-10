"""Test query filtering by scope, kind, status."""

from datetime import datetime, timedelta, timezone

import pytest

from continuity.api.models import (
    Basis,
    CommitMemoryRequest,
    MemoryKind,
    MemoryStatus,
    ObserveMemoryRequest,
    QueryMemoryRequest,
    RelianceClass,
    RevokeMemoryRequest,
)
from continuity.store.sqlite import SQLiteStore


def _observe(store: SQLiteStore, scope: str, kind: MemoryKind) -> str:
    resp = store.observe_memory(ObserveMemoryRequest(
        scope=scope,
        kind=kind,
        basis=Basis.DIRECT_CAPTURE,
        content={"test": f"{scope}/{kind}"},
    ))
    return resp.memory.memory_id


def test_query_by_scope(store: SQLiteStore) -> None:
    _observe(store, "project-a", MemoryKind.FACT)
    _observe(store, "project-a", MemoryKind.NOTE)
    _observe(store, "project-b", MemoryKind.FACT)

    resp = store.query_memory(QueryMemoryRequest(scope="project-a"))
    assert resp.total == 2
    assert all(m.scope == "project-a" for m in resp.items)


def test_query_by_kind(store: SQLiteStore) -> None:
    _observe(store, "proj", MemoryKind.FACT)
    _observe(store, "proj", MemoryKind.HYPOTHESIS)
    _observe(store, "proj", MemoryKind.FACT)

    resp = store.query_memory(QueryMemoryRequest(kind=MemoryKind.FACT))
    assert resp.total == 2


def test_query_by_status(store: SQLiteStore) -> None:
    mid = _observe(store, "proj", MemoryKind.DECISION)
    _observe(store, "proj", MemoryKind.NOTE)

    store.commit_memory(CommitMemoryRequest(
        memory_id=mid,
        reliance_class=RelianceClass.ADVISORY,
    ))

    resp = store.query_memory(QueryMemoryRequest(
        status=MemoryStatus.COMMITTED,
    ))
    assert resp.total == 1
    assert resp.items[0].memory_id == mid


def test_query_pagination(store: SQLiteStore) -> None:
    for i in range(5):
        _observe(store, "proj", MemoryKind.NOTE)

    page1 = store.query_memory(QueryMemoryRequest(scope="proj", limit=2, offset=0))
    page2 = store.query_memory(QueryMemoryRequest(scope="proj", limit=2, offset=2))

    assert page1.total == 5
    assert len(page1.items) == 2
    assert len(page2.items) == 2
    assert page1.items[0].memory_id != page2.items[0].memory_id


def test_literal_text_composes_with_filters_and_pagination(store: SQLiteStore) -> None:
    for scope in ("case:a", "case:a", "case:b"):
        store.observe_memory(ObserveMemoryRequest(
            scope=scope, kind="experiment", basis="import",
            content={"action": "Storage retirement 50%_complete"},
        ))
    first = store.query_memory(QueryMemoryRequest(scope="case:a", text="RETIREMENT", limit=1))
    second = store.query_memory(QueryMemoryRequest(scope="case:a", text="retirement", limit=1, offset=1))
    assert first.total == second.total == 2
    assert first.items[0].memory_id != second.items[0].memory_id
    assert store.query_memory(QueryMemoryRequest(text="50%_")).total == 3
    assert store.query_memory(QueryMemoryRequest(text="50%X")).total == 0
    assert store.query_memory(QueryMemoryRequest(text="' OR 1=1 --")).total == 0
    assert store.query_memory(QueryMemoryRequest(text="action", kind="note")).total == 0
    assert store.query_memory(QueryMemoryRequest(text="action")).total == 3  # keys too
    assert store.query_memory(QueryMemoryRequest()).total == 3  # unchanged default


def test_text_does_not_hide_revocation_or_change_expiration(store: SQLiteStore) -> None:
    now = datetime.now(timezone.utc)
    expired = store.observe_memory(ObserveMemoryRequest(
        scope="history", kind="note", basis="import", content={"text": "retirement"},
        expires_at=now - timedelta(days=1),
    ))
    revoked = store.observe_memory(ObserveMemoryRequest(
        scope="history", kind="note", basis="import", content={"text": "retirement"},
    ))
    store.revoke_memory(RevokeMemoryRequest(memory_id=revoked.memory.memory_id, reason="disputed"))
    visible = store.query_memory(QueryMemoryRequest(text="retirement"))
    assert [m.memory_id for m in visible.items] == [revoked.memory.memory_id]
    assert visible.items[0].status == "revoked"
    assert store.query_memory(QueryMemoryRequest(text="retirement", include_expired=True)).total == 2
    assert expired.memory.memory_id != revoked.memory.memory_id


@pytest.mark.parametrize("text", ["", "  ", "\n", "x" * 257])
def test_text_refuses_empty_or_unbounded_queries(text: str) -> None:
    with pytest.raises(ValueError):
        QueryMemoryRequest(text=text)
