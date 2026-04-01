"""
Agent Session Management.

This module contains the AgentSession class which represents a single
interactive session with the Claude Agent SDK, managing the client
connection, permission callbacks, and conversation state.
"""

from app.core.config import get_settings


class AgentSession:
    """
    Represents a single Claude Agent session.

    Manages the SDK client, permission callbacks, and conversation state
    for one interactive session.
    """

    def __init__(
        self,
        session_id: str,
        model: str | None = None,
        background_model: str | None = None,
    ):
        self.session_id = session_id
        self.model = model or get_settings().ANTHROPIC_MODEL
        self.background_model = (
            background_model or get_settings().ANTHROPIC_SMALL_FAST_MODEL
        )  # Background model for agents
        self.current_model = self.model  # Track current model for status
        # Session configuration
        if not cwd:
            cwd = get_settings().WORKSPACE_BASE_PATH
        self.cwd = cwd
