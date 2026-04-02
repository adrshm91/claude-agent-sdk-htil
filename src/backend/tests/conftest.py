"""
Shared test configuration and fixtures.
"""

from unittest.mock import MagicMock

import pytest
from app.core.session import AgentSession
from app.core.session_manager import SessionManager


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager for use across tests."""
    manager = MagicMock(spec=SessionManager)
    manager.current_session_id = None
    manager.current_session = None
    manager.get_session = MagicMock()
    manager.create_session = MagicMock()
    return manager


@pytest.fixture
def mock_agent_session():
    """Create a mock agent session for use across tests."""
    session = MagicMock(spec=AgentSession)
    session.session_id = "test-session-id"
    session.user_id = "test-user"
    session.status = "connected"
    return session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Add any global test setup here
    yield
    # Add any global test cleanup here
