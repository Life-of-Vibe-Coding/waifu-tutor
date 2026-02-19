"""Sync repo skills into OpenViking using add_skill (directory with SKILL.md + auxiliary files)."""
from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings
from app.db.openviking_client import get_openviking_client

logger = logging.getLogger(__name__)


def get_skills_source_dir() -> Path:
    """Return the project's skills directory (repo skills to migrate)."""
    # openviking_data_dir is PROJECT_ROOT/db/data/openviking
    data_dir = get_settings().openviking_data_dir.resolve()
    project_root = data_dir.parent.parent.parent
    return project_root / "skills"


def sync_skills_into_openviking() -> None:
    """
    Add each skill under the repo's skills/ directory into OpenViking.
    Follows docs/openviking/04-skills.md: add_skill(directory) includes SKILL.md and auxiliary files.
    """
    if not get_settings().openviking_config_file.resolve().exists():
        logger.info("OpenViking config missing; skip skill sync.")
        return
    skills_dir = get_skills_source_dir()
    if not skills_dir.is_dir():
        logger.info("Skills directory not found at %s; skip skill sync.", skills_dir)
        return
    client = get_openviking_client()
    added = 0
    for path in sorted(skills_dir.iterdir()):
        if not path.is_dir():
            continue
        skill_md = path / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            raw = client.add_skill(str(path.resolve()), wait=True)
            result = raw.get("result", raw) if isinstance(raw, dict) else {}
            uri = result.get("uri") or result.get("name", path.name)
            logger.info("OpenViking skill added: %s -> %s", path.name, uri)
            added += 1
        except Exception as e:
            logger.exception("OpenViking add_skill failed for %s: %s", path.name, e)
    if added:
        logger.info("OpenViking skills sync done: %d skill(s) added.", added)
