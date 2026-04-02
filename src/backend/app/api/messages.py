import json
import logging

from app.core.session_manager import SessionManager
from app.models.schemas import SendMessageRequest, SendMessageResponse
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["messages"])


def get_session_manager(request: Request) -> SessionManager:
    """
    Dependency to get the session manager from application state.

    Args:
        request: FastAPI request object containing app state

    Returns:
        SessionManager instance from app.state

    Raises:
        RuntimeError: If session manager is not initialized in app state
    """
    if not hasattr(request.app.state, "session_manager"):
        raise RuntimeError("Session manager not initialized in app state")
    return request.app.state.session_manager


def safe_json_dumps(obj):
    """
    Safely serialize objects to JSON, handling non-serializable objects.

    Args:
        obj: Object to serialize

    Returns:
        JSON string
    """

    def default_handler(o):
        # Handle objects with __dict__ attribute
        if hasattr(o, "__dict__"):
            return o.__dict__
        # Handle other non-serializable types
        return str(o)

    return json.dumps(obj, default=default_handler)


@router.post("/messages/stream")
async def send_message_stream(
    message_request: SendMessageRequest,
    resume_session_id: str | None = None,
    manager: SessionManager = Depends(get_session_manager),
):

    if not resume_session_id:
        session = await manager.create_session()
    else:
        session = await manager.get_session(resume_session_id)

    async def event_generator():
        """Generate SSE events from the agent response."""
        event_count = 0
        try:
            async for event in session.send_message_stream(message_request.message):
                event_count += 1
                logger.debug(
                    f"Event #{event_count}: type={event.get('type', 'unknown')}"
                )

                # Add session_id to each event for frontend session management
                if isinstance(event, dict):
                    event["session_id"] = session.session_id
                elif isinstance(event, str):
                    # For string events, wrap in a dict with session_id
                    event = {
                        "type": "text",
                        "content": event,
                        "session_id": session.session_id,
                    }

                # Format as SSE: data: {json}\n\n
                # Use safe_json_dumps to handle non-serializable objects
                yield f"data: {safe_json_dumps(event)}\n\n"
            logger.debug(
                f"========== send_message_stream END (total events: {event_count}) ==========\n"
            )
        except Exception as e:
            logger.debug("========== send_message_stream ERROR ==========")
            logger.error(f"Exception: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.debug("================================================\n")
            # Send error event with session_id
            error_event = {
                "type": "error",
                "error": str(e),
                "session_id": session.session_id,
            }
            yield f"data: {safe_json_dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/messages", response_model=SendMessageResponse)
async def send_message(
    message_request: SendMessageRequest,
    resume_session_id: str | None = None,
    manager: SessionManager = Depends(get_session_manager),
):
    if not resume_session_id:
        session = await manager.create_session()
    else:
        session = await manager.get_session(resume_session_id)
    return await session.send_message(message_request.message)
