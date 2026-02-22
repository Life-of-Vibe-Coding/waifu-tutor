from __future__ import annotations

from app.api import chat as chat_api

def test_run_tool_loop_returns_typed_fallback_result_on_empty_turn(monkeypatch):

    def fake_agent_run(self, agno_msgs, **kwargs):
        class MockRunOutput:
            @property
            def messages(self):
                return agno_msgs
        return MockRunOutput()

    monkeypatch.setattr("agno.agent.Agent.run", fake_agent_run)

    run_res = chat_api._run_tool_loop(
        messages=[{"role": "user", "content": "write essay"}],
        session_id="s1",
        user_id="u1",
        user_timezone=None,
    )

    assert run_res.text is None
    assert run_res.used_fallback is True
    assert run_res.reminder_payload is None
    assert run_res.hitl_payload is None


def test_complete_chat_does_not_call_ai_fallback_when_loop_returns_text(monkeypatch):
    def fake_run_tool_loop(messages, session_id, user_id, user_timezone=None):
        return chat_api.AgentRunResult(
            text="Recovery text",
            used_fallback=True,
            reminder_payload=None,
            hitl_payload=None,
        )

    def fail_ai_chat(*args, **kwargs):
        raise AssertionError("ai_chat fallback should not be called when tool loop already returned text")

    monkeypatch.setattr(chat_api, "_run_tool_loop", fake_run_tool_loop)
    monkeypatch.setattr(chat_api, "ai_chat", fail_ai_chat)
    monkeypatch.setattr(chat_api, "get_agent_context_text", lambda: "")

    run_res = chat_api._complete_chat(
        msg="yes please",
        context_texts=[],
        attachment_title=None,
        history=[],
        session_id="s1",
        user_id="u1",
        user_timezone=None,
    )

    assert run_res.text == "Recovery text"
    assert run_res.used_fallback is True
    assert run_res.reminder_payload is None
    assert run_res.hitl_payload is None
