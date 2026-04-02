"""
Agent Session Management.

This module contains the AgentSession class which represents a single
interactive session with the Claude Agent SDK, managing the client
connection, permission callbacks, and conversation state.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.models.schemas import MessageBlock, SendMessageResponse
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    CLINotFoundError,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class AgentSession:
    """
    Represents a single Claude Agent session.

    Manages the SDK client, permission callbacks, and conversation state
    for one interactive session.
    """

    def __init__(
        self,
        model: str | None = None,
        background_model: str | None = None,
        cwd: str | None = None,
    ):
        self.status = "initializing"
        self.session_id = None  # Will be set upon message send/receive
        self.last_activity = datetime.now(timezone.utc)
        self.created_at = datetime.now(timezone.utc)
        self.message_count = 0

        self.model = model or get_settings().ANTHROPIC_MODEL
        self.background_model = (
            background_model or get_settings().ANTHROPIC_SMALL_FAST_MODEL
        )  # Background model for agents

        # Permission management
        self.pending_permission: dict[str, Any] | None = None
        self.permission_event: asyncio.Event | None = None
        self.permission_result: Any | None = None
        self.permission_queue: asyncio.Queue = asyncio.Queue(
            maxsize=get_settings().PERMISSION_QUEUE_SIZE
        )  # Bounded queue for permission events

        # Session configuration
        if not cwd:
            cwd = get_settings().WORKSPACE_BASE_PATH
        self.cwd = cwd

        self.client: ClaudeSDKClient | None = None

    async def connect(self, resume_session_id: str | None = None):
        """
        Connect to the Claude SDK and initialize the session.

        Args:
            resume_session_id: Optional session ID to resume a previous session
        """
        options_dict = {
            "allowed_tools": [],
            "max_turns": 0,  # No limit on turns
            # "can_use_tool": self.permission_callback,  # Permission callback for tool usage
            "permission_mode": "default",
        }
        if resume_session_id:
            options_dict["resume"] = resume_session_id
        if self.model:
            options_dict["model"] = self.model

        if self.cwd:
            options_dict["cwd"] = self.cwd

        # Add setting_sources to load user plugins
        options_dict["setting_sources"] = ["user", "project"]

        options = ClaudeAgentOptions(**options_dict)
        try:
            logger.info("Connecting to Claude SDK...")

            self.client = ClaudeSDKClient(options=options)

            await self.client.connect()
            self.status = "connected"
            logger.info("✓ Connected successfully")
        except (CLINotFoundError, CLIConnectionError) as e:
            self.status = "error"
            raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")

    async def disconnect(self):
        """
        Disconnect the session and clean up resources.
        """
        if self.client:
            try:
                await self.client.disconnect()
            except RuntimeError as e:
                # Handle anyio TaskGroup exit in different task error
                # This can happen when closing sessions due to asyncio event loop differences
                if "cancel scope" in str(e) or "different task" in str(e):
                    # Log the error but don't fail - the session is being closed anyway
                    logger.warning(
                        f"Session {self.session_id}: Disconnect cleanup error (non-fatal): {e}"
                    )
                else:
                    raise
            finally:
                self.status = "disconnected"

    async def send_message_stream(self, message: str | dict):
        """
        Send a message and stream the response in real-time.

        Args:
            message: The user's message (string or structured UserMessage dict)

        Yields:
            Dictionary events with type and data for each step

        Raises:
            HTTPException: If session not connected
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")
        self.last_activity = datetime.now(timezone.utc)

        self.message_count += 1

        # Simple string message (including AskUserQuestion answers)
        await self.client.query(message)

        # Track last reported permission to avoid duplicates
        last_permission_id = None

        # Create a task to receive SDK responses
        response_iterator = self.client.receive_response()

        # Flag to track if we're done
        sdk_done = False

        async def get_next_msg():
            return await anext(response_iterator)

        while not sdk_done:
            sdk_task = asyncio.create_task(get_next_msg())

            while not sdk_task.done():
                # Check permission queue first (non-blocking)
                try:
                    permission = self.permission_queue.get_nowait()
                    permission_id = permission.get("request_id")
                    logger.debug(f"🚨 FOUND PERMISSION IN QUEUE: {permission_id}")
                    if permission_id != last_permission_id:
                        logger.debug(
                            "send_message_stream: Got permission from queue, sending event"
                        )
                        logger.debug(f"🚨 YIELDING PERMISSION EVENT: {permission}")
                        yield {"type": "permission", "permission": permission}
                        last_permission_id = permission_id
                    else:
                        logger.debug(
                            f"🚨 SKIPPING DUPLICATE PERMISSION: {permission_id}"
                        )
                except asyncio.QueueEmpty:
                    pass

                await asyncio.sleep(0.05)

            try:
                msg = sdk_task.result()
            except StopAsyncIteration:
                # SDK response stream is done
                logger.debug("✅ SDK response stream completed")
                sdk_done = True
                break
            if isinstance(msg, SystemMessage):
                # System message - typically informational, log but don't send to client
                logger.debug(f"SystemMessage content: {msg}")
                logger.debug(f"SystemMessage attributes: {dir(msg)}")
                if hasattr(msg, "content"):
                    logger.debug(f"SystemMessage.content: {msg.content}")
                if hasattr(msg, "text"):
                    logger.debug(f"SystemMessage.text: {msg.text}")
                self.session_id = getattr(msg, "session_id", None) or getattr(
                    msg, "data", {}
                ).get("session_id", None)
                logger.info(
                    f"Agent initialized - Claude Agent SDK Session ID: {self.session_id}"
                )
                # Continue to next message
                continue
            elif isinstance(msg, UserMessage):
                # User message event
                logger.debug(f"UserMessage.content: {msg.content}")
                logger.debug(
                    f"UserMessage.role: {msg.role if hasattr(msg, 'role') else 'N/A'}"
                )
                yield {"type": "user_message", "content": msg.content}
            elif isinstance(msg, AssistantMessage):
                # Assistant message with content blocks
                logger.debug(
                    f"  AssistantMessage.role: {msg.role if hasattr(msg, 'role') else 'N/A'}"
                )
                logger.debug(
                    f"  AssistantMessage.model: {msg.model if hasattr(msg, 'model') else 'N/A'}"
                )
                logger.debug(f"  Full message object: {msg}")

                for i, block in enumerate(msg.content):
                    if isinstance(block, TextBlock):
                        yield {"type": "text", "content": block.text}
                    elif isinstance(block, ToolUseBlock):
                        yield {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_input": block.input,
                            "tool_use_id": block.id,
                        }
                    else:
                        logger.debug(f"    Block content: {block}")
            elif isinstance(msg, ResultMessage):
                logger.debug("send_message_stream: Received ResultMessage")
                logger.debug(f"  total_cost_usd: {msg.total_cost_usd}")
                logger.debug(f"  num_turns: {msg.num_turns}")
                # Final result with metadata

                logger.debug("Yielding 'result' event")
                yield {
                    "type": "result",
                    "cost_usd": msg.total_cost_usd,
                    "num_turns": msg.num_turns,
                    "session_id": self.session_id,
                }
        # Check for any remaining permissions in queue before finishing
        logger.debug("Checking for remaining permissions in queue...")
        while True:
            try:
                permission = self.permission_queue.get_nowait()
                permission_id = permission.get("request_id")
                if permission_id != last_permission_id:
                    logger.debug(
                        "send_message_stream: Got final permission from queue, sending event"
                    )
                    yield {"type": "permission", "permission": permission}
                    last_permission_id = permission_id
            except asyncio.QueueEmpty:
                break

        # Send completion event with real session_id
        yield {
            "type": "done",
            "session_id": self.session_id,
        }

    async def send_message(self, message: str | dict) -> SendMessageResponse:
        """
        Send a message and get the response.

        Args:
            message: The user's message (string or structured UserMessage dict)

        Returns:
            SendMessageResponse with assistant's reply

        Raises:
            HTTPException: If session not connected
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")
        self.last_activity = datetime.now(timezone.utc)
        self.message_count += 1

        await self.client.query(message)

        # Collect response
        messages = []
        cost_usd = None
        num_turns = None

        async for msg in self.client.receive_response():
            if isinstance(msg, SystemMessage):
                # Skip system messages
                logger.debug("send_message: Skipping SystemMessage")
                self.session_id = getattr(msg, "session_id", None) or getattr(
                    msg, "data", {}
                ).get("session_id", None)
                pass
            elif isinstance(msg, UserMessage):
                # Skip user messages in response
                logger.debug("send_message: Skipping UserMessage")
                pass
            elif isinstance(msg, AssistantMessage):
                logger.debug(
                    f"send_message: Processing AssistantMessage with {len(msg.content)} blocks"
                )
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        messages.append(MessageBlock(type="text", content=block.text))
                    elif isinstance(block, ToolUseBlock):
                        messages.append(
                            MessageBlock(
                                type="tool_use",
                                tool_name=block.name,
                                tool_input=block.input,
                            )
                        )
            elif isinstance(msg, ResultMessage):
                logger.debug("send_message: Received ResultMessage")
                cost_usd = msg.total_cost_usd
                num_turns = msg.num_turns

        return SendMessageResponse(
            messages=messages,
            session_id=self.session_id,
            cost_usd=cost_usd,
            num_turns=num_turns,
        )

    async def interrupt(self):
        """
        Interrupt the current operation.

        Raises:
            HTTPException: If session not connected or SDK call fails
        """
        if not self.client or self.status != "connected":
            raise HTTPException(status_code=400, detail="Session not connected")

        try:
            await self.client.interrupt()
            self.last_activity = datetime.now(timezone.utc)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to interrupt: {str(e)}"
            )
