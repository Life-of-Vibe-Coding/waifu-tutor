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
print("Content:", res.content)
print("Tool calls:", getattr(res, "tool_calls", "No tool_calls attr"))
if res.messages:
    last_msg = res.messages[-1]
    print("Last msg tool calls:", getattr(last_msg, "tool_calls", "No tool_calls"))
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        print(last_msg.tool_calls)
