import json
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
from agno.tools import Function
from app.core.config import get_settings

hitl_data = None

def my_tool(msg: str):
    global hitl_data
    hitl_data = {"msg": msg}
    return "__HITL_PAUSE__"

func = Function(
    name="my_tool",
    description="Ask human",
    parameters={"type": "object", "properties": {"msg": {"type": "string"}}},
    entrypoint=my_tool,
    stop_after_tool_call=True
)

settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    tools=[func],
    skills=skills,
    add_history_to_context=True,
    num_history_messages=10,
)

res = agent.run("Please call my_tool with 'Hello'")
print("hitl_data:", hitl_data)
if getattr(res, "messages", None):
    print("Messages:", [m.role for m in res.messages])
