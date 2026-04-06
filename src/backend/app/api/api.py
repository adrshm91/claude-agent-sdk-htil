from app.api.messages import router as messages_router
from app.api.permissions import router as permissions_router
from fastapi import APIRouter

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(messages_router)
api_router.include_router(permissions_router)
