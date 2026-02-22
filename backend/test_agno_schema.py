from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
from app.core.config import get_settings

settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    tools=[{"type": "function", "function": {"name": "get_weather", "description": "Get weather", "parameters": {"type": "object", "properties": {"loc": {"type": "string"}}}}}],
    skills=skills,
)

res = agent.run("What is the weather in Tokyo?")
if res.messages:
    last_msg = res.messages[-1]
    if getattr(last_msg, "tool_calls", None):
        print("Model asked for tool call:", last_msg.tool_calls[0])
    elif res.content:
        print("Model replied:", res.content)
