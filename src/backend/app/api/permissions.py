import logging

from app.core.session_manager import SessionManager
from app.models.schemas import PermissionResponse
from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["permissions"])


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


@router.post("/permissions/respond")
async def respond_to_permission(
    session_id: str,
    response: PermissionResponse,
    manager: SessionManager = Depends(get_session_manager),
):
    """
    Respond to a pending permission request.

    Args:
        session_id: The session ID
        response: Permission response

    Returns:
        Success message
    """
    session = await manager.get_session(session_id)
    session.respond_to_permission(
        request_id=response.request_id,
        allowed=response.allowed,
        apply_suggestions=response.apply_suggestions,
        answers=response.answers,
    )
    return {"status": "ok"}
