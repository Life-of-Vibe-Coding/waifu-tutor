from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
from agno.tools import Function
import json
from app.core.config import get_settings

def request_approval(msg: str):
    return json.dumps({"status": "Waiting for human approval", "msg": msg})

func = Function(
    name="request_approval",
    description="Ask human for approval",
    parameters={"type": "object", "properties": {"msg": {"type": "string"}}},
    entrypoint=request_approval,
    stop_after_tool_call=True
)

settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    tools=[func],
    skills=skills,
)

res = agent.run("Please ask me for approval with message 'Hello'")
print("Stopped? ", "waiting" in res.content if res.content else "No content")
if getattr(res, "messages", None):
    for m in res.messages:
        if m.role == "tool":
            print("Tool returned:", m.content)
