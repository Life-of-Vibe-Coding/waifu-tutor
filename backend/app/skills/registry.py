"""Build skill registry from YAML frontmatter of top-level SKILL.md files."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REGISTRY: list[dict[str, str]] = []


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Parse YAML frontmatter from markdown content. Returns dict of top-level string values."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    result: dict[str, str] = {}
    for line in block.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip("'\"").strip()
            if key and value:
                result[key] = value
    return result


def build_skill_registry(skills_root: Path) -> list[dict[str, Any]]:
    """Scan skills_root for top-level folders with SKILL.md; read only YAML frontmatter.
    Returns list of { name, description } for each skill. Subskills are not registered.
    """
    global _REGISTRY
    _REGISTRY = []
    root = Path(skills_root)
    if not root.is_dir():
        logger.warning("Skills root is not a directory: %s", root)
        return _REGISTRY
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            raw = skill_md.read_text(encoding="utf-8", errors="replace")
            fm = _parse_frontmatter(raw)
            name = fm.get("name") or entry.name
            description = fm.get("description", "").strip() or f"Skill: {entry.name}"
            _REGISTRY.append({"name": name, "description": description})
        except Exception as e:
            logger.warning("Skip skill %s: %s", entry.name, e)
    logger.info("Skill registry built: %d skill(s) from %s", len(_REGISTRY), root)
    return list(_REGISTRY)


def get_skill_registry() -> list[dict[str, Any]]:
    """Return cached registry. Empty if build_skill_registry() has not been called."""
    return list(_REGISTRY)


def get_skills_root() -> Path:
    """Return the configured skills root (from settings). Lazy import to avoid circular deps."""
    from app.core.config import get_settings
    return Path(get_settings().skills_dir)
