"""Agent harness for skill and tool execution."""
from app.agent.config import AgentConfig, get_default_agent_config
from app.agent.harness import AgentHarness, create_agent

_default_agent: AgentHarness | None = None


def get_default_agent() -> AgentHarness:
    """Return the default agent harness, creating it on first call."""
    global _default_agent
    if _default_agent is None:
        _default_agent = create_agent(get_default_agent_config())
    return _default_agent


def set_default_agent(agent: AgentHarness | None) -> None:
    """Set the default agent (for testing or custom config)."""
    global _default_agent
    _default_agent = agent


__all__ = [
    "AgentConfig",
    "AgentHarness",
    "create_agent",
    "get_default_agent",
    "get_default_agent_config",
    "set_default_agent",
]
