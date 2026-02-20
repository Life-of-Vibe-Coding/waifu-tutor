"""Agent harness configuration."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for the agent harness."""

    skills_root: Path
    tools: list[dict[str, Any]]
    system_prompt: str = ""
    max_tool_rounds: int = 20
    max_empty_response_retries: int = 4


def get_default_agent_config() -> AgentConfig:
    """Build default agent config from app settings and tool modules."""
    from app.core.config import get_settings
    from app.tool.tools import CHAT_TOOLS

    settings = get_settings()
    skills_root = Path(settings.skills_dir)
    return AgentConfig(
        skills_root=skills_root,
        tools=CHAT_TOOLS,
        max_tool_rounds=20,
        max_empty_response_retries=4,
    )
