"""Shared test helper: create a shape-valid fake gitdir.

The root-discovery hardening (2026-07-26) validates ``.git`` markers the way
git does — HEAD + objects/ + refs/ — so tests that simulate "inside a repo"
must create markers with that shape rather than a bare ``mkdir``.
"""

from __future__ import annotations

from pathlib import Path


def make_gitdir(parent: Path) -> Path:
    """Create a minimal shape-valid ``.git`` directory under ``parent``."""
    gitdir = parent / ".git"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n")
    (gitdir / "objects").mkdir()
    (gitdir / "refs").mkdir()
    return gitdir
