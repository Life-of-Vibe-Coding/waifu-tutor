"""Tests for skill registry and load_subskill path safety."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.skills.registry import build_skill_registry, get_skill_registry, _parse_frontmatter


def _safe_resolve(root: Path, path_str: str) -> Path | None:
    """Same logic as load_subskill._safe_resolve: resolve under root, reject .. and absolute."""
    path_str = (path_str or "").strip().replace("\\", "/")
    if not path_str or path_str.startswith("/") or ".." in path_str.split("/"):
        return None
    parts = [p for p in path_str.split("/") if p and p != "."]
    resolved = root
    for p in parts:
        resolved = resolved / p
    try:
        resolved = resolved.resolve()
        root_resolved = root.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            return None
        return resolved
    except Exception:
        return None


def test_parse_frontmatter():
    md = """---
name: exam-mode-tuner
description: Runs adaptive practice exams.
---
# Title
"""
    fm = _parse_frontmatter(md)
    assert fm.get("name") == "exam-mode-tuner"
    assert "adaptive" in (fm.get("description") or "")


def test_parse_frontmatter_empty():
    assert _parse_frontmatter("no frontmatter") == {}
    assert _parse_frontmatter("---\n---") == {}


def test_build_skill_registry(tmp_path: Path):
    (tmp_path / "skill-a").mkdir()
    (tmp_path / "skill-a" / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: First skill\n---\n# A\n"
    )
    (tmp_path / "skill-b").mkdir()
    (tmp_path / "skill-b" / "SKILL.md").write_text(
        "---\nname: skill-b\ndescription: Second\n---\n# B\n"
    )
    (tmp_path / "not-a-skill").mkdir()  # no SKILL.md
    reg = build_skill_registry(tmp_path)
    assert len(reg) == 2
    names = {r["name"] for r in reg}
    assert names == {"skill-a", "skill-b"}


def test_safe_resolve_no_escape(tmp_path: Path):
    root = tmp_path / "skills"
    root.mkdir()
    (root / "a").mkdir()
    (root / "a" / "b").mkdir()
    (root / "a" / "b" / "c.md").write_text("")
    assert _safe_resolve(root, "a/b/c.md") is not None
    assert _safe_resolve(root, "exam-mode-tuner/sub/skill.md") is not None
    assert _safe_resolve(root, "") is None
    assert _safe_resolve(root, "/etc/passwd") is None
    assert _safe_resolve(root, "..") is None
    assert _safe_resolve(root, "a/../b") is None
    assert _safe_resolve(root, "a/..") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
