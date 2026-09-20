"""Receipt output formatting.

Receipts are already stored in the database as ReceiptRecord objects.
This module provides output formatting for CLI emission and future
spool/file export.

The envelope shape is continuity's own:
  - receipt_id
  - receipt_type
  - hash (content hash, chained from prev_hash)
  - prev_hash (chain linkage)
  - timestamp
  - payload (the receipt content)

The envelope previously claimed compatibility with the retired WLP
protocol. That claim is withdrawn: WLP has no named consumer, and this
envelope is not held to any external format. Signatures, a canonical
encoding version, and transport metadata remain unimplemented and are
not owed to anyone.
"""

from __future__ import annotations

from typing import Any

from continuity.api.models import ReceiptRecord
from continuity.util.clock import to_isoformat


def format_receipt(receipt: ReceiptRecord) -> dict[str, Any]:
    """Format a ReceiptRecord as a continuity receipt envelope dict.

    This is what gets emitted to stdout, written to spool files,
    or eventually shipped over the wire.
    """
    return {
        "envelope": "continuity.receipt.v0",
        "receipt_id": receipt.receipt_id,
        "receipt_type": receipt.receipt_type,
        "hash": receipt.hash,
        "prev_hash": receipt.prev_hash,
        "timestamp": to_isoformat(receipt.created_at),
        "payload": receipt.content,
    }


def format_receipt_chain(receipts: list[ReceiptRecord]) -> list[dict[str, Any]]:
    """Format a list of receipts as an ordered chain."""
    return [format_receipt(r) for r in receipts]
