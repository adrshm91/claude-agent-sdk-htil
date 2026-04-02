import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import yaml
from app.api.api import api_router
from app.core.config import get_settings
from app.core.session_manager import SessionManager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load logging configuration from YAML file
with open("app/logging_config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

LOG_LEVEL = logging.getLevelName(logger.getEffectiveLevel())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 API Server Starting...")
    logger.info(f"📝 Log Level: {LOG_LEVEL}")
    logger.info("=" * 80)

    # Initialize session manager and store in app state
    app.state.session_manager = SessionManager()
    logger.info("✅ Session manager initialized")

    # Ensure workspace directory exists
    workspace_path = get_settings().WORKSPACE_BASE_PATH
    try:
        from pathlib import Path

        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Workspace directory: {workspace_path}")
        logger.info("✅ Workspace directory ready")
    except Exception as e:
        logger.error(f"❌ Failed to create workspace directory {workspace_path}: {e}")

    logger.info("=" * 80)
    logger.info("✅ Server startup complete")
    logger.info("=" * 80)

    yield

    # Shutdown - close all sessions
    logger.info("🛑 Shutting down server...")
    if hasattr(app.state, 'session_manager'):
        await app.state.session_manager.close_session()

    logger.info("✅ Server shutdown complete")


def get_app() -> FastAPI:
    """App Factory."""
    logger.info(get_settings().fastapi_kwargs)
    app = FastAPI(
        **get_settings().fastapi_kwargs,
        lifespan=lifespan,
    )

    # Add CORS middleware to allow web client access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )

    # Health check endpoint (not under API prefix)
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Docker and load balancers."""
        return {"status": "healthy", "version": get_settings().VERSION}

    # Include API routes
    settings = get_settings()
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = get_app()

# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health_check(request):
    """Health check endpoint."""
    active_sessions = 0
    if hasattr(request.app.state, 'session_manager'):
        active_sessions = 1 if request.app.state.session_manager.has_active_session() else 0

    return {
        "status": "healthy",
        "active_sessions": active_sessions,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ping")
async def ping():
    """Ping endpoint for health monitoring."""
    import time

    return {"status": "Healthy", "time_of_last_update": int(time.time())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
