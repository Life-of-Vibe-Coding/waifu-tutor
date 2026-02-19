from __future__ import annotations

from app.api import chat as chat_api


def test_run_tool_loop_returns_recovery_after_repeated_empty_turns(monkeypatch):
    calls = {"n": 0}

    def fake_complete_with_tools(messages, tools):
        calls["n"] += 1
        return None, None, "thinking"

    monkeypatch.setattr(chat_api, "complete_with_tools", fake_complete_with_tools)

    text, used_fallback, reminder, hitl = chat_api._run_tool_loop(
        messages=[{"role": "user", "content": "write essay"}],
        session_id="s1",
        user_id="u1",
        user_timezone=None,
    )

    assert text is not None
    assert "temporary generation issue" in text.lower()
    assert used_fallback is True
    assert reminder is None
    assert hitl is None
    assert calls["n"] == chat_api.MAX_EMPTY_RESPONSE_RETRIES + 1


def test_complete_chat_does_not_call_ai_fallback_when_loop_returns_text(monkeypatch):
    def fake_run_tool_loop(messages, session_id, user_id, user_timezone=None):
        return "Recovery text", True, None, None

    def fail_ai_chat(*args, **kwargs):
        raise AssertionError("ai_chat fallback should not be called when tool loop already returned text")

    monkeypatch.setattr(chat_api, "_run_tool_loop", fake_run_tool_loop)
    monkeypatch.setattr(chat_api, "ai_chat", fail_ai_chat)
    monkeypatch.setattr(chat_api, "get_agent_context_text", lambda: "")

    text, used_fallback, reminder, hitl = chat_api._complete_chat(
        msg="yes please",
        context_texts=[],
        attachment_title=None,
        history=[],
        session_id="s1",
        user_id="u1",
        user_timezone=None,
    )

    assert text == "Recovery text"
    assert used_fallback is True
    assert reminder is None
    assert hitl is None
