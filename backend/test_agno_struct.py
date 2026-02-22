from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.models.message import Message
from agno.skills import Skills, LocalSkills
from app.core.config import get_settings

msg = Message(role="user", content="hello")
print("Message args:", msg.role, msg.content)

settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    skills=skills,
)
print("Has memory? ", hasattr(agent, "memory"))
if hasattr(agent, "memory"):
    print("Memory class: ", type(agent.memory))
