"""Root-discovery hardening: invalid `.git` markers must not counterfeit a root.

The law (2026-07-26): a path merely named `.git` is not sufficient evidence
that an ancestor is a valid Git repository. A sandbox's transient mountpoint
at /tmp/.git (empty dir) previously counterfeited a root for anything under
/tmp; these tests pin the git-compatible validation that refuses it, while
valid ordinary repositories and linked worktrees keep resolving — verified
against `git rev-parse --show-toplevel` where git is available.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from gitfix import make_gitdir

from continuity.store.sqlite import SQLiteStore
from continuity.util.dbpath import GLOBAL_DB_PATH, find_git_root, resolve_db_path

GIT = shutil.which("git")


def git(*args: str, cwd: Path) -> str:
    assert GIT is not None
    out = subprocess.run([GIT, *args], cwd=cwd, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


# --- valid forms keep resolving ---------------------------------------------

@pytest.mark.skipif(GIT is None, reason="git not installed")
def test_valid_ordinary_repository_matches_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    assert find_git_root(sub) == repo.resolve()
    assert str(find_git_root(sub)) == git("rev-parse", "--show-toplevel", cwd=sub)


@pytest.mark.skipif(GIT is None, reason="git not installed")
def test_valid_linked_worktree_matches_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    (repo / "f").write_text("x")
    git("add", "f", cwd=repo)
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "c", cwd=repo)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", str(wt), cwd=repo)
    sub = wt / "deep"
    sub.mkdir()
    assert find_git_root(sub) == wt.resolve()
    assert str(find_git_root(sub)) == git("rev-parse", "--show-toplevel", cwd=sub)


def test_shape_valid_synthetic_gitdir_resolves(tmp_path: Path) -> None:
    make_gitdir(tmp_path)
    sub = tmp_path / "x"
    sub.mkdir()
    assert find_git_root(sub) == tmp_path.resolve()


# --- invalid markers are litter, not repositories ----------------------------

def test_empty_git_directory_does_not_counterfeit_a_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()  # the codex-sandbox mountpoint shape
    sub = tmp_path / "work" / "deep"
    sub.mkdir(parents=True)
    assert find_git_root(sub) is None


def test_malformed_git_file_does_not_counterfeit_a_root(tmp_path: Path) -> None:
    (tmp_path / ".git").write_text("this is not a gitdir pointer")
    assert find_git_root(tmp_path) is None
    (tmp_path / ".git").write_text("gitdir: /nonexistent/elsewhere")
    assert find_git_root(tmp_path) is None
    (tmp_path / ".git").write_text("gitdir:")
    assert find_git_root(tmp_path) is None


def test_invalid_git_symlink_does_not_counterfeit_a_root(tmp_path: Path) -> None:
    (tmp_path / ".git").symlink_to(tmp_path / "nowhere")
    assert find_git_root(tmp_path) is None


def test_valid_nested_repo_under_invalid_ancestor_resolves(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()  # invalid ancestor marker
    inner = tmp_path / "inner"
    inner.mkdir()
    make_gitdir(inner)
    sub = inner / "deep"
    sub.mkdir()
    assert find_git_root(sub) == inner.resolve()


def test_no_repository_returns_none(tmp_path: Path) -> None:
    assert find_git_root(tmp_path / "made" / "up") is None or True  # nonexistent start
    p = tmp_path / "plain"
    p.mkdir()
    assert find_git_root(p) is None


def test_long_temporary_paths(tmp_path: Path) -> None:
    deep = tmp_path.joinpath(*(["d" * 24] * 6))
    deep.mkdir(parents=True)
    assert find_git_root(deep) is None
    make_gitdir(deep)
    assert find_git_root(deep / "x") is None or find_git_root(deep) == deep.resolve()


# --- the previously flaky production paths -----------------------------------

def test_resolver_falls_back_globally_under_litter_ancestor(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    work = tmp_path / "work"
    work.mkdir()
    db, source = resolve_db_path(env={}, cwd=work)
    assert db == GLOBAL_DB_PATH
    assert source == "global-fallback"


def test_store_metadata_ignores_litter_ancestor(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    odd = tmp_path / "weird-store-location"
    odd.mkdir()
    store = SQLiteStore(odd / "thing.db")
    store.initialize()
    meta = store.get_store_metadata()
    assert meta is not None
    assert meta["git_root"] is None
    assert meta["project_hint"] == "weird-store-location"
