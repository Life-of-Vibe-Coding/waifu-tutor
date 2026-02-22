import sys
from app.api.chat import _complete_chat
from app.agent import get_default_agent
from pydantic import BaseModel

class DummyRequest(BaseModel):
    pass

res = _complete_chat(
    msg="Tell me a very short joke.",
    context_texts=[],
    attachment_title=None,
    history=[],
    session_id="test_session_agno",
    user_id="test_user",
    user_timezone="UTC"
)

print(f"Chat Response: {res.text}")
if res.hitl_payload:
    print(f"HITL Payload Triggered: {res.hitl_payload}")
