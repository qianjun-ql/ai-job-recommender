"""Tests for FR-08 — Agentic RAG Chatbot (api/services/chatbot.py).

All Gemini / LangGraph calls are mocked so tests run without an API key,
internet access, or a loaded FAISS index.

Covers:
    _extract_sources   — job_id extraction from ToolMessages
    _extract_tool_names — tool call extraction from AIMessages
    agent_chat          — full chat loop (mocked graph)
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from api.models import ChatResponse
from api.services.chatbot import _extract_sources, _extract_tool_names, agent_chat

# ── Patch targets ──────────────────────────────────────────────────────────────

_GET_LLM = "api.services.chatbot._get_llm"
_CREATE_AGENT = "api.services.chatbot.create_react_agent"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _tool_message(content: str, name: str = "search_jobs") -> ToolMessage:
    return ToolMessage(content=content, tool_call_id="tc_abc", name=name)


def _ai_message_with_tools(*tool_names: str) -> AIMessage:
    """AIMessage that has pending tool_calls (mid-turn, not the final answer)."""
    tool_calls = [{"name": n, "args": {}, "id": f"tc_{n}"} for n in tool_names]
    return AIMessage(content="", tool_calls=tool_calls)


def _ai_message_final(content: str) -> AIMessage:
    """Final AIMessage with no pending tool_calls."""
    return AIMessage(content=content)


def _make_graph(messages: list[Any]) -> MagicMock:
    """Return a mock LangGraph graph whose invoke() returns the given messages."""
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {"messages": messages}
    return mock_graph


# ── TestExtractSources ─────────────────────────────────────────────────────────


class TestExtractSources:
    def test_extracts_job_ids_from_search_jobs_tool_message(self) -> None:
        msg = _tool_message("[job_001] ML Engineer | [job_002] AI Engineer")
        sources = _extract_sources([msg])
        assert "job_001" in sources
        assert "job_002" in sources

    def test_ignores_non_search_jobs_tool_messages(self) -> None:
        msg = _tool_message("[job_999] ignored", name="get_skill_gap")
        sources = _extract_sources([msg])
        assert sources == []

    def test_deduplicates_job_ids(self) -> None:
        msg1 = _tool_message("[job_001] ML Engineer")
        msg2 = _tool_message("[job_001] ML Engineer (duplicate)")
        sources = _extract_sources([msg1, msg2])
        assert sources.count("job_001") == 1

    def test_preserves_order(self) -> None:
        msg = _tool_message("[job_003] C | [job_001] A | [job_002] B")
        sources = _extract_sources([msg])
        assert sources == ["job_003", "job_001", "job_002"]

    def test_empty_messages_returns_empty_list(self) -> None:
        assert _extract_sources([]) == []

    def test_non_tool_messages_ignored(self) -> None:
        human = HumanMessage(content="[job_999] not a tool message")
        ai = _ai_message_final("[job_888] also not a tool message")
        assert _extract_sources([human, ai]) == []

    def test_returns_job_ids_across_multiple_search_messages(self) -> None:
        msg1 = _tool_message("[job_001] first")
        msg2 = _tool_message("[job_002] second")
        sources = _extract_sources([msg1, msg2])
        assert sources == ["job_001", "job_002"]


# ── TestExtractToolNames ───────────────────────────────────────────────────────


class TestExtractToolNames:
    def test_extracts_tool_name_from_ai_message_dict_format(self) -> None:
        msg = _ai_message_with_tools("search_jobs")
        names = _extract_tool_names([msg])
        assert names == ["search_jobs"]

    def test_extracts_multiple_tools_in_call_order(self) -> None:
        msg1 = _ai_message_with_tools("search_jobs")
        msg2 = _ai_message_with_tools("get_skill_gap")
        names = _extract_tool_names([msg1, msg2])
        assert names == ["search_jobs", "get_skill_gap"]

    def test_deduplicates_tool_names(self) -> None:
        msg1 = _ai_message_with_tools("search_jobs")
        msg2 = _ai_message_with_tools("search_jobs")
        names = _extract_tool_names([msg1, msg2])
        assert names.count("search_jobs") == 1

    def test_ignores_ai_messages_without_tool_calls(self) -> None:
        msg = _ai_message_final("Here is your answer.")
        names = _extract_tool_names([msg])
        assert names == []

    def test_empty_messages_returns_empty_list(self) -> None:
        assert _extract_tool_names([]) == []

    def test_human_messages_ignored(self) -> None:
        human = HumanMessage(content="any message")
        names = _extract_tool_names([human])
        assert names == []

    def test_multiple_tools_in_single_ai_message(self) -> None:
        msg = _ai_message_with_tools("search_jobs", "get_trending_skills")
        names = _extract_tool_names([msg])
        assert "search_jobs" in names
        assert "get_trending_skills" in names


# ── TestAgentChat ──────────────────────────────────────────────────────────────


class TestAgentChat:
    """Tests for the main agent_chat() entrypoint."""

    _BASE_MESSAGES = [
        HumanMessage(content="What ML Engineer jobs are hiring?"),
        _ai_message_with_tools("search_jobs"),
        _tool_message("[job_001] ML Engineer in Calgary | score=0.95"),
        _ai_message_final("Based on job_001, ML Engineers in Calgary need PyTorch and AWS."),
    ]

    def _run_chat(
        self,
        messages: list[Any] | None = None,
        message: str = "What jobs are hiring?",
        session_id: str = "session-abc",
        user_skills: list[str] | None = None,
    ) -> ChatResponse:
        if messages is None:
            messages = self._BASE_MESSAGES
        if user_skills is None:
            user_skills = ["Python", "SQL"]
        graph = _make_graph(messages)
        with patch(_GET_LLM, return_value=MagicMock()), patch(_CREATE_AGENT, return_value=graph):
            return agent_chat(message=message, session_id=session_id, user_skills=user_skills)

    def test_returns_chat_response(self) -> None:
        result = self._run_chat()
        assert isinstance(result, ChatResponse)

    def test_session_id_echoed(self) -> None:
        result = self._run_chat(session_id="my-unique-session")
        assert result.session_id == "my-unique-session"

    def test_answer_extracted_from_final_ai_message(self) -> None:
        result = self._run_chat()
        assert "job_001" in result.answer or "PyTorch" in result.answer

    def test_answer_skips_ai_messages_with_tool_calls(self) -> None:
        """The mid-turn AIMessage (with tool_calls) must not be used as the answer."""
        messages = [
            _ai_message_with_tools("search_jobs"),  # mid-turn, has tool_calls
            _tool_message("[job_001] ML Engineer"),
            _ai_message_final("Final answer here."),
        ]
        result = self._run_chat(messages=messages)
        assert result.answer == "Final answer here."

    def test_sources_populated_from_search_tool_messages(self) -> None:
        result = self._run_chat()
        assert "job_001" in result.sources

    def test_tool_calls_made_populated(self) -> None:
        result = self._run_chat()
        assert "search_jobs" in result.tool_calls_made

    def test_empty_user_skills_accepted(self) -> None:
        result = self._run_chat(user_skills=[])
        assert isinstance(result, ChatResponse)

    def test_graph_invoke_receives_human_message(self) -> None:
        graph = _make_graph(self._BASE_MESSAGES)
        with patch(_GET_LLM, return_value=MagicMock()), patch(_CREATE_AGENT, return_value=graph):
            agent_chat(message="Hello", session_id="s1", user_skills=[])

        call_kwargs = graph.invoke.call_args
        messages_arg = call_kwargs[0][0]["messages"]
        assert any(isinstance(m, HumanMessage) for m in messages_arg)

    def test_graph_invoke_receives_session_id_as_thread_id(self) -> None:
        graph = _make_graph(self._BASE_MESSAGES)
        with patch(_GET_LLM, return_value=MagicMock()), patch(_CREATE_AGENT, return_value=graph):
            agent_chat(message="Hello", session_id="sess-xyz", user_skills=[])

        # config is passed as a keyword argument: graph.invoke({...}, config={...})
        config = graph.invoke.call_args.kwargs["config"]
        assert config["configurable"]["thread_id"] == "sess-xyz"

    def test_exception_in_graph_invoke_returns_graceful_error(self) -> None:
        graph = MagicMock()
        graph.invoke.side_effect = RuntimeError("LLM quota exceeded")
        with patch(_GET_LLM, return_value=MagicMock()), patch(_CREATE_AGENT, return_value=graph):
            result = agent_chat(message="Boom", session_id="s1", user_skills=[])

        assert isinstance(result, ChatResponse)
        assert "error" in result.answer.lower()
        assert result.sources == []
        assert result.tool_calls_made == []

    def test_error_response_still_echoes_session_id(self) -> None:
        graph = MagicMock()
        graph.invoke.side_effect = RuntimeError("network error")
        with patch(_GET_LLM, return_value=MagicMock()), patch(_CREATE_AGENT, return_value=graph):
            result = agent_chat(message="Hi", session_id="err-session", user_skills=[])

        assert result.session_id == "err-session"

    def test_no_final_ai_message_returns_empty_answer(self) -> None:
        """If the graph returns only tool/human messages, answer should be empty."""
        messages = [
            HumanMessage(content="hi"),
            _tool_message("[job_001] some job"),
        ]
        result = self._run_chat(messages=messages)
        assert result.answer == ""

    def test_multiple_tool_calls_all_captured(self) -> None:
        messages = [
            _ai_message_with_tools("search_jobs"),
            _tool_message("[job_001] ML Engineer"),
            _ai_message_with_tools("get_skill_gap"),
            _tool_message("Match score: 60%", name="get_skill_gap"),
            _ai_message_final("You match 60% of ML Engineer requirements."),
        ]
        result = self._run_chat(messages=messages)
        assert "search_jobs" in result.tool_calls_made
        assert "get_skill_gap" in result.tool_calls_made
