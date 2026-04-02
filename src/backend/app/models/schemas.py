from typing import Any

from pydantic import BaseModel


class CreateSessionResponse(BaseModel):
    """Response containing new session information."""

    session_id: str
    created_at: str
    status: str


class CreateSessionRequest(BaseModel):
    """Request to create a new session or resume an existing one."""

    user_id: str | None = None  # User ID for S3 sync tracking
    resume_session_id: str | None = None
    model: str | None = None  # e.g., "claude-3-5-sonnet-20241022"
    background_model: str | None = (
        None  # Background model for agents (sets ANTHROPIC_DEFAULT_HAIKU_MODEL)
    )
    cwd: str | None = None  # Working directory for the session
    mcp_server_ids: list[str] | None = None  # List of MCP server names to enable


class SendMessageRequest(BaseModel):
    """Request to send a message in a session."""

    message: (
        str | dict[str, Any]
    )  # Can be string or structured message (e.g., with tool_result)


class MessageBlock(BaseModel):
    """Represents a single content block in a message."""

    type: str  # "text", "tool_use", "thinking"
    content: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None


class SendMessageResponse(BaseModel):
    """Response containing assistant's reply."""

    messages: list[MessageBlock]
    session_id: str
    cost_usd: float | None = None
    num_turns: int | None = None
