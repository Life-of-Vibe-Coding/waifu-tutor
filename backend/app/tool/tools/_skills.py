"""Shared helpers for viking/agent/skills filesystem access."""
from __future__ import annotations

import re
from pathlib import Path

from app.db.openviking_client import get_openviking_path

SKILLS_BASE_REL = ("viking", "agent", "skills")


def _repo_skills_dir() -> Path | None:
    """Return the project's skills/ directory (repo root), or None if it does not exist."""
    # backend/app/tool/tools/_skills.py -> project root is 5 levels up
    try:
        base = Path(__file__).resolve().parent.parent.parent.parent.parent
    except Exception:
        return None
    path = base / "skills"
    return path if path.is_dir() else None


def skills_dir() -> Path | None:
    """Return the viking/agent/skills directory path, or repo skills/ as fallback, or None."""
    base = get_openviking_path()
    path = base.joinpath(*SKILLS_BASE_REL)
    if path.is_dir():
        return path
    return _repo_skills_dir()


def _read_abstract(path: Path, fallback_md: Path | None, max_len: int = 200) -> str:
    """Read .abstract.md or first paragraph of a markdown file."""
    abstract_file = path / ".abstract.md"
    if abstract_file.is_file():
        return abstract_file.read_text(encoding="utf-8", errors="replace").strip()
    if fallback_md and fallback_md.is_file():
        text = fallback_md.read_text(encoding="utf-8", errors="replace")
        first = text.split("\n\n")[0].strip()
        return first[:max_len] if first else ""
    return ""


def _description_from_frontmatter(md_path: Path) -> str | None:
    """Extract description from YAML frontmatter in a markdown file."""
    if not md_path.is_file():
        return None
    text = md_path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    block = match.group(1)
    for line in block.split("\n"):
        if line.strip().lower().startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"").strip('"')[:300]
    return None


def list_skills_from_fs(include_subskills: bool = True) -> list[dict[str, str]]:
    """List skills under viking/agent/skills: name and abstract (or short description).
    When include_subskills is True, also lists subskills as parent_skill/subskill_name so
    the agent can discover and call get_skill for them."""
    root = skills_dir()
    if not root:
        return []
    out: list[dict[str, str]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        skill_md = path / "SKILL.md"
        if not skill_md.is_file():
            continue
        desc = _read_abstract(path, skill_md)
        out.append({"name": path.name, "description": desc})
        if not include_subskills:
            continue
        for sub_path in sorted(path.iterdir()):
            if not sub_path.is_dir():
                continue
            sub_md = sub_path / f"{sub_path.name}.md"
            if not sub_md.is_file():
                sub_md = sub_path / "SKILL.md"
            if not sub_md.is_file():
                md_files = [f for f in sub_path.iterdir() if f.suffix == ".md"]
                sub_md = md_files[0] if md_files else None
            if sub_md is None or not sub_md.is_file():
                continue
            sub_desc = _description_from_frontmatter(sub_md) or _read_abstract(sub_path, sub_md, max_len=180)
            composite_name = f"{path.name}/{sub_path.name}"
            out.append({"name": composite_name, "description": f"[subskill of {path.name}] {sub_desc}"})
    return out


def get_skill_content(skill_name: str, level: str) -> str | None:
    """Get skill content by name. level: 'abstract' | 'overview' | 'full'. Returns None if not found.
    skill_name may be a top-level skill (e.g. 'memory-comprehension-coach') or a subskill path
    (e.g. 'memory-comprehension-coach/mastery-diagnosis') to load the subskill's .md file."""
    root = skills_dir()
    if not root:
        return None
    if "/" in skill_name:
        parent, sub_name = skill_name.split("/", 1)
        parent_dir = root / parent
        sub_dir = parent_dir / sub_name
        if not sub_dir.is_dir():
            return None
        sub_md = sub_dir / f"{sub_name}.md"
        if not sub_md.is_file():
            sub_md = sub_dir / "SKILL.md"
        if not sub_md.is_file():
            md_in_dir = [f for f in sub_dir.iterdir() if f.suffix == ".md"]
            sub_md = md_in_dir[0] if md_in_dir else None
        if sub_md is None or not sub_md.is_file():
            return None
        if level in ("abstract", "overview"):
            abstract = sub_dir / ".abstract.md"
            if abstract.is_file():
                return abstract.read_text(encoding="utf-8", errors="replace").strip()
            overview = sub_dir / ".overview.md"
            if overview.is_file():
                return overview.read_text(encoding="utf-8", errors="replace").strip()
            text = sub_md.read_text(encoding="utf-8", errors="replace")
            first = text.split("\n\n")[0]
            return first.strip()[:500] if first else text.strip()[:500]
        return sub_md.read_text(encoding="utf-8", errors="replace").strip()
    skill_dir = root / skill_name
    if not skill_dir.is_dir():
        return None
    if level == "abstract":
        p = skill_dir / ".abstract.md"
        return p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else None
    if level == "overview":
        p = skill_dir / ".overview.md"
        return p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else None
    if level == "full":
        p = skill_dir / "SKILL.md"
        return p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else None
    return None
