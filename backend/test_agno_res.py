import json
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.models.message import Message
from agno.skills import Skills, LocalSkills
from agno.tools import Function
from app.core.config import get_settings

def fake_tool(msg: str):
    return "done"

func = Function(name="fake_tool", description="fake", parameters={"type": "object", "properties": {"msg": {"type": "string"}}}, entrypoint=fake_tool, stop_after_tool_call=True)

settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    tools=[func],
    skills=skills,
)

msgs = [{"role": "user", "content": "Please call fake_tool."}]
agno_msgs = [Message(role=m["role"], content=m["content"]) for m in msgs]

res = agent.run(agno_msgs)

print("Response content:", res.content)
print("Response type:", type(res))
if hasattr(res, "messages"):
    print("Messages attr exists! Length:", len(res.messages))
    for i, m in enumerate(res.messages):
        print(f"[{i}] {m.role}: {m.content}")
        if hasattr(m, "tool_calls") and m.tool_calls:
            print(f"    Tool calls: {[t for t in m.tool_calls]}")
else:
    print("No messages attr in run response")
