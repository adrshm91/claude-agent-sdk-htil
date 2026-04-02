"""
Unit tests for the messages API endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request

from app.api.messages import send_message_stream, router
from app.models.schemas import SendMessageRequest
from app.core.session_manager import SessionManager
from app.core.session import AgentSession


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = MagicMock(spec=SessionManager)
    manager.current_session_id = None
    manager.current_session = None
    manager.get_session = AsyncMock()
    manager.create_session = AsyncMock()
    return manager


@pytest.fixture
def mock_agent_session():
    """Create a mock agent session."""
    session = MagicMock(spec=AgentSession)
    session.session_id = "test-session-id"
    return session


@pytest.fixture
def send_message_request():
    """Create a test send message request."""
    return SendMessageRequest(message="Hello, Claude!")


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = MagicMock(spec=Request)
    request.headers = {"x-amzn-bedrock-agentcore-runtime-session-id": "bedrock-session-123"}
    return request


class TestSendMessageStream:
    """Test cases for the send_message_stream endpoint."""

    @patch('app.api.messages.get_session_manager')
    async def test_create_new_session_when_no_current_session(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request,
        mock_request
    ):
        """Test creating a new session when no current session exists."""
        # Arrange
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = None
        mock_session_manager.create_session.return_value = mock_agent_session

        # Act
        await send_message_stream(send_message_request, mock_request)

        # Assert
        mock_session_manager.create_session.assert_called_once()
        assert mock_session_manager.get_session.call_count == 0

    @patch('app.api.messages.get_session_manager')
    async def test_use_existing_session_when_session_ids_match(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request,
        mock_request
    ):
        """Test using existing session when session IDs match."""
        # Arrange
        bedrock_session_id = "bedrock-session-123"
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = bedrock_session_id
        mock_session_manager.get_session.return_value = mock_agent_session

        # Act
        await send_message_stream("test-session-id", send_message_request, mock_request)

        # Assert
        mock_session_manager.get_session.assert_called_once_with(bedrock_session_id)
        assert mock_session_manager.create_session.call_count == 0

    @patch('app.api.messages.get_session_manager')
    async def test_create_new_session_when_session_ids_dont_match(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request,
        mock_request
    ):
        """Test creating new session when session IDs don't match."""
        # Arrange
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = "different-session-id"
        mock_session_manager.create_session.return_value = mock_agent_session

        # Act
        await send_message_stream(send_message_request, mock_request)

        # Assert
        mock_session_manager.create_session.assert_called_once()
        assert mock_session_manager.get_session.call_count == 0

    @patch('app.api.messages.get_session_manager')
    async def test_handles_missing_bedrock_session_header(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request
    ):
        """Test handling when bedrock session header is missing."""
        # Arrange
        mock_request_no_header = MagicMock(spec=Request)
        mock_request_no_header.headers.get = MagicMock(return_value=None)

        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = "some-session-id"
        mock_session_manager.create_session.return_value = mock_agent_session

        # Act
        await send_message_stream("test-session-id", send_message_request, mock_request_no_header)

        # Assert
        # When header is missing, agentcore_session_id will be None
        # This should trigger creation of a new session since None != "some-session-id"
        mock_session_manager.create_session.assert_called_once()

    @patch('app.api.messages.get_session_manager')
    async def test_handles_none_bedrock_session_header_value(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request
    ):
        """Test handling when bedrock session header value is None."""
        # Arrange
        mock_request_none_header = MagicMock(spec=Request)
        mock_request_none_header.headers.get.return_value = None

        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = None
        mock_session_manager.get_session.return_value = mock_agent_session

        # Act
        await send_message_stream("test-session-id", send_message_request, mock_request_none_header)

        # Assert
        # When both are None, they match, so existing session should be used
        mock_session_manager.get_session.assert_called_once_with(None)

    def test_get_session_manager_imports_correctly(self):
        """Test that get_session_manager imports the session manager correctly."""
        # This test verifies the import path works without actually importing main
        from app.api.messages import get_session_manager

        # The function should exist and be callable
        assert callable(get_session_manager)

    @patch('app.api.messages.get_session_manager')
    async def test_different_message_types(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        mock_request
    ):
        """Test with different message types (string vs dict)."""
        # Arrange
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = None
        mock_session_manager.create_session.return_value = mock_agent_session

        # Test with string message
        string_request = SendMessageRequest(message="Hello, Claude!")

        # Test with dict message
        dict_request = SendMessageRequest(
            message={"text": "Hello", "type": "user"}
        )

        # Act & Assert - Both should work the same way
        await send_message_stream("test-session-id", string_request, mock_request)
        mock_session_manager.create_session.assert_called()

        mock_session_manager.reset_mock()

        await send_message_stream("test-session-id", dict_request, mock_request)
        mock_session_manager.create_session.assert_called()


# Integration test (mocked but more realistic)
class TestSendMessageStreamIntegration:
    """Integration tests for send_message_stream with more realistic scenarios."""

    def test_endpoint_signature_compatibility(self):
        """Test that the endpoint has the correct signature."""
        from app.api.messages import send_message_stream
        import inspect

        # Check that the function has the expected parameters
        sig = inspect.signature(send_message_stream)
        params = list(sig.parameters.keys())

        assert "session_id" in params
        assert "message_request" in params
        assert "request" in params

        # Function should be a coroutine (async)
        assert inspect.iscoroutinefunction(send_message_stream)


class TestSessionManagerSessionHandling:
    """Test cases for session manager's handling of non-existent sessions."""

    @patch('app.api.messages.get_session_manager')
    async def test_get_session_falls_back_to_create_when_session_not_found(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request,
        mock_request
    ):
        """Test that get_session creates a new session when the requested session doesn't exist."""
        # Arrange
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = "different-session-id"

        # Mock get_session to raise an exception (simulating session not found in Claude)
        from fastapi import HTTPException
        mock_session_manager.get_session.side_effect = Exception("Session not found")

        # Mock create_session to succeed
        mock_session_manager.create_session.return_value = mock_agent_session

        # Act
        await send_message_stream("test-session-id", send_message_request, mock_request)

        # Assert
        # The get_session should be called first (which will fail)
        # Then create_session should be called as fallback
        mock_session_manager.get_session.assert_called_once()
        mock_session_manager.create_session.assert_called_once()

    @patch('app.api.messages.get_session_manager')
    async def test_get_session_succeeds_when_session_exists(
        self,
        mock_get_session_manager,
        mock_session_manager,
        mock_agent_session,
        send_message_request,
        mock_request
    ):
        """Test that get_session works normally when the session exists."""
        # Arrange
        bedrock_session_id = "bedrock-session-123"
        mock_get_session_manager.return_value = mock_session_manager
        mock_session_manager.current_session_id = bedrock_session_id
        mock_session_manager.get_session.return_value = mock_agent_session

        # Act
        await send_message_stream("test-session-id", send_message_request, mock_request)

        # Assert
        # Only get_session should be called, no create_session
        mock_session_manager.get_session.assert_called_once_with(bedrock_session_id)
        assert mock_session_manager.create_session.call_count == 0