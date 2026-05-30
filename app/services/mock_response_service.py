"""
app/services/mock_response_service.py
---------------------------------------
Placeholder service that returns a canned response without calling any LLM.

Why a separate module?
    When you're ready to add a real model, you replace (or extend) only this
    file.  The graph, schemas, and main.py stay unchanged.
"""

from __future__ import annotations


def generate_mock_response(message: str) -> str:
    """Return a deterministic mock answer for the given message.

    Args:
        message: The user message from the request.

    Returns:
        A readable string confirming the local stack is working.
    """
    return (
        f"Hello! Local AgentCore + LangGraph setup is working. "
        f"You said: {message}"
    )
