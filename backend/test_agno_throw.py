from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
class HitlException(Exception): pass
def my_tool():
    raise HitlException("pause!")

from app.core.config import get_settings
settings = get_settings()
skills = Skills(loaders=[LocalSkills(path=settings.skills_dir, validate=False)])
agent = Agent(
    model=OpenAIResponses(id=settings.chat_model, api_key=settings.volcengine_api_key, base_url=settings.volcengine_chat_base.rstrip("/")),
    tools=[my_tool],
    skills=skills,
)
try:
    agent.run("Call my_tool.")
except HitlException:
    print("Caught HitlException!")
