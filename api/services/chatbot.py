"""
FR-08 — Agentic RAG Chatbot

LangGraph stateful tool-calling agent (Gemini 2.0 Flash) that answers career
questions grounded in real job-posting data via 4 tools:

    search_jobs(query)                       — FAISS semantic search over 10k postings
    get_skill_gap(role)                      — FR-05 gap analysis for user vs. role
    get_trending_skills(role)                — demand-ranked top 10 skills per role
    recommend_projects(missing, target_role) — FR-06 portfolio project ideas

Conversation history: LangGraph MemorySaver checkpointer (per session_id /
thread_id). History persists in-process — replace with a Redis-backed
checkpointer for multi-replica deployments.

@observe() is a no-op stub here — FR-11 replaces it with real Langfuse tracing
without any change to this file's logic.
"""

from __future__ import annotations

import logging
import re
from functools import wraps
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from api.models import ChatResponse
from api.services import gap as gap_service
from api.services import matcher as matcher_service
from api.services import recommender as recommender_service
from config.settings import settings

logger = logging.getLogger(__name__)


# ── No-op @observe stub (FR-11 replaces with real Langfuse decorator) ──────────


def observe(fn=None, *, name: str | None = None):
    """No-op trace decorator — FR-11 wires this to Langfuse."""
    if fn is None:
        return lambda f: f

    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    return wrapper


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an AI career advisor with access to tools. "
    "Use tools to answer questions grounded in real job data. "
    "Always cite which job postings informed your answer by including job_ids "
    "(e.g. job_124, job_891) in your response. "
    "Never answer from memory alone — always call at least one tool first. "
    "Be concise, actionable, and specific."
)


# ── Global checkpointer (in-process conversation memory) ─────────────────────
#
# MemorySaver stores message history keyed by thread_id (= session_id).
# All sessions share one saver; history is differentiated by "thread_id" in
# the runnable config passed on each graph.invoke() call.
_memory_saver = MemorySaver()


# ── LLM factory (lazy singleton) ──────────────────────────────────────────────

_llm: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    """Lazy-load Gemini 2.0 Flash (shared across requests)."""
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.GEMINI_API_KEY or None,
            temperature=0.1,
        )
    return _llm


# ── Tool factory ─────────────────────────────────────────────────────────────


def _build_tools(user_skills: list[str]) -> list:
    """
    Build the 4 agent tools, closing over ``user_skills`` so each tool
    automatically has the caller's skill context without extra plumbing.
    """

    @tool
    def search_jobs(query: str) -> str:
        """Search the job database semantically.

        Returns top-5 job postings matching the query with job_ids, titles,
        roles, locations, match scores and required skills.
        Use this for questions about the job market, what roles exist, or what
        companies are hiring.
        """
        try:
            results = matcher_service.search_by_query(query, top_k=5)
            if not results:
                return "No matching jobs found for that query."
            lines: list[str] = []
            for j in results:
                skills_preview = ", ".join(j.skills[:5]) if j.skills else "N/A"
                lines.append(
                    f"[{j.job_id}] {j.title} ({j.role}) in {j.location} "
                    f"| score={j.match_score:.2f} | skills: {skills_preview}"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("search_jobs tool error: %s", exc)
            return f"search_jobs encountered an error: {exc}"

    @tool
    def get_skill_gap(role: str) -> str:
        """Compute the skill gap between the user's current skills and a target role.

        Returns matched skills, missing skills, and an overall match score (%).
        role must be exactly one of:
            AI Engineer, Data Engineer, Data Scientist, ML Engineer, SWE
        """
        try:
            result = gap_service.compute_gap(user_skills, role)
            missing_str = ", ".join(result.missing_skills) if result.missing_skills else "none"
            matched_str = ", ".join(result.matched_skills) if result.matched_skills else "none"
            return (
                f"Role: {result.target_role} | "
                f"Match score: {result.match_score:.0f}% | "
                f"Already have: {matched_str} | "
                f"Missing: {missing_str}"
            )
        except ValueError as exc:
            return f"Invalid role — {exc}"
        except Exception as exc:
            logger.warning("get_skill_gap tool error: %s", exc)
            return f"get_skill_gap encountered an error: {exc}"

    @tool
    def get_trending_skills(role: str) -> str:
        """Get the top 10 most in-demand skills for a role, ranked by job posting frequency.

        role must be exactly one of:
            AI Engineer, Data Engineer, Data Scientist, ML Engineer, SWE
        """
        try:
            skills = gap_service.get_top_skills(role, n=10)
            if not skills:
                return "No skill data available for this role."
            lines = [
                f"{s.skill}: {s.demand_count} jobs ({s.pct_of_jobs * 100:.0f}%)" for s in skills
            ]
            return "\n".join(lines)
        except ValueError as exc:
            return f"Invalid role — {exc}"
        except Exception as exc:
            logger.warning("get_trending_skills tool error: %s", exc)
            return f"get_trending_skills encountered an error: {exc}"

    @tool
    def recommend_projects(missing_skills: str, target_role: str) -> str:
        """Generate 2-3 portfolio project ideas to close skill gaps.

        missing_skills: comma-separated skills to address (e.g. "PyTorch, Docker, AWS")
        target_role: one of AI Engineer, Data Engineer, Data Scientist, ML Engineer, SWE
        """
        try:
            gaps = [s.strip() for s in missing_skills.split(",") if s.strip()]
            if not gaps:
                return "Please provide at least one missing skill (comma-separated)."
            projects = recommender_service.recommend_projects(
                missing_skills=gaps,
                user_skills=user_skills,
                target_role=target_role,
                n=3,
            )
            if not projects:
                return "Could not generate project ideas — please try again."
            parts: list[str] = []
            for p in projects:
                skills_str = ", ".join(p.skills_addressed)
                desc = p.description[:140].rstrip()
                parts.append(
                    f"• {p.title} ({p.estimated_hours}h, {p.difficulty})\n"
                    f"  {desc}...\n"
                    f"  Skills addressed: {skills_str}"
                )
            return "\n\n".join(parts)
        except Exception as exc:
            logger.warning("recommend_projects tool error: %s", exc)
            return f"recommend_projects encountered an error: {exc}"

    return [search_jobs, get_skill_gap, get_trending_skills, recommend_projects]


# ── Result extraction ────────────────────────────────────────────────────────

_JOB_ID_RE = re.compile(r"\[([^\]\s,]+)\]")


def _extract_sources(messages: list[Any]) -> list[str]:
    """
    Pull job_id strings from search_jobs ToolMessage responses.
    Example content: "[job_124] ML Engineer (ML Engineer) in Calgary | ..."
    """
    sources: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "search_jobs":
            sources.extend(_JOB_ID_RE.findall(str(msg.content)))
    return list(dict.fromkeys(sources))  # deduplicate, preserve order


def _extract_tool_names(messages: list[Any]) -> list[str]:
    """Return names of tools actually invoked, deduplicated in call order."""
    seen: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name and name not in seen:
                    seen.append(name)
    return seen


# ── Public entry point ────────────────────────────────────────────────────────


@observe
def agent_chat(
    message: str,
    session_id: str,
    user_skills: list[str],
) -> ChatResponse:
    """
    Run one conversational turn through the tool-calling agent.

    Args:
        message:     User's question or message.
        session_id:  Client-supplied UUID for conversation continuity.
                     Maps to the LangGraph thread_id for history persistence.
        user_skills: Caller's skills — injected into all tool closures so that
                     gap analysis and project recommendations are personalised.

    Returns:
        ChatResponse with the agent's answer, cited job_ids, tools used,
        and the echoed session_id.

    Never raises — all exceptions produce a graceful error ChatResponse.
    """
    tools = _build_tools(user_skills)
    llm = _get_llm()

    # Build a fresh graph on each call — it's stateless (history in _memory_saver).
    # Rebuilding per request ensures user_skills changes are reflected immediately.
    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=_SYSTEM_PROMPT,
        checkpointer=_memory_saver,
    )

    config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
    except Exception as exc:
        logger.error("agent_chat error session=%s: %s", session_id, exc)
        return ChatResponse(
            answer=(
                "I encountered an error processing your request. "
                "Please try again or rephrase your question."
            ),
            sources=[],
            tool_calls_made=[],
            session_id=session_id,
        )

    messages: list[Any] = result.get("messages", [])

    # Final AI response: last AIMessage without pending tool_calls
    answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            answer = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    return ChatResponse(
        answer=answer,
        sources=_extract_sources(messages),
        tool_calls_made=_extract_tool_names(messages),
        session_id=session_id,
    )
