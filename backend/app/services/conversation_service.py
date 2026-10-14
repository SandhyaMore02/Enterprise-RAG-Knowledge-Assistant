"""
Enterprise RAG Knowledge Assistant — Conversation Service

Manages multi-turn conversation memory and contextual question reformulating.
Resolves pronouns and follow-up references before retrieval.

Phase 8 of the implementation plan.
"""

import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 6

REWRITE_PROMPT = """Given a conversation history between a user and an assistant, and a follow-up question from the user, rephrase the follow-up question to be a standalone, self-contained question that can be understood without the conversation history.

Do NOT answer the question. Only return the rephrased standalone question.
If the question is already self-contained, return it unchanged.

Conversation History:
{history}

Follow-up Question: {question}

Standalone Question:"""


class ConversationService:
    """
    In-memory conversation session store and query contextualizer.
    """

    def __init__(self, llm=None) -> None:
        self.sessions: dict[str, list[dict[str, str]]] = {}
        self.llm = llm

    def create_session(self) -> str:
        """Create a new conversation session ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []
        return session_id

    def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Retrieve recent conversation history for a session."""
        return self.sessions.get(conversation_id, [])

    def add_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Record a turn in the conversation history with sliding window limit."""
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = []

        self.sessions[conversation_id].append({
            "user": user_message,
            "assistant": assistant_message,
        })

        # Keep history within reasonable window
        if len(self.sessions[conversation_id]) > MAX_HISTORY_TURNS:
            self.sessions[conversation_id] = self.sessions[conversation_id][-MAX_HISTORY_TURNS:]

    def contextualize_query(self, question: str, conversation_id: str | None) -> str:
        """
        Rephrase follow-up questions into standalone search queries.
        If history exists and contains pronouns/ellipses, rewrites the query.
        """
        if not conversation_id or conversation_id not in self.sessions:
            return question

        history = self.sessions[conversation_id]
        if not history:
            return question

        # Format history string
        history_lines = []
        for turn in history:
            history_lines.append(f"User: {turn['user']}")
            history_lines.append(f"Assistant: {turn['assistant']}")
        formatted_history = "\n".join(history_lines)

        # If LLM is available, rephrase using LLM
        if self.llm is not None:
            try:
                prompt = REWRITE_PROMPT.format(
                    history=formatted_history,
                    question=question,
                )
                response = self.llm.invoke([HumanMessage(content=prompt)])
                rewritten = response.content if hasattr(response, "content") else str(response)
                rewritten = rewritten.strip()
                logger.info("Rewrote query '%s' -> '%s'", question, rewritten)
                return rewritten
            except Exception as e:
                logger.warning("Query rewriting failed: %s. Using original query.", e)
                return question

        # Offline / Heuristic fallback for pronoun resolution
        lower_q = question.lower().strip()
        follow_up_triggers = ["what about", "how about", "and for", "why", "their", "them", "it", "they"]
        if any(lower_q.startswith(trig) for trig in ["what about", "how about", "and for"]) and history:
            last_user_q = history[-1]["user"]
            # Combine previous context topic with current query
            combined = f"{last_user_q} - {question}"
            return combined

        return question
