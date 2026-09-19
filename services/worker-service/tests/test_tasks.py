"""
Unit tests for task handlers
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from app.tasks import (
    process_llm_request,
    process_approval_create,
    process_approval_update,
    process_email_notification,
    process_slack_notification,
    TaskRegistry,
    ApprovalRecord,
    NotificationLog,
    LLMRequestLog
)
from app.config import settings


@pytest.mark.asyncio
class TestTaskHandlers:
    """Test task handler functions."""

    async def test_process_llm_request_success(
        self,
        task_context,
        sample_llm_message,
        mock_httpx_client,
        monkeypatch
    ):
        """Test successful LLM request processing."""
        monkeypatch.setattr('httpx.AsyncClient', mock_httpx_client)

        context = task_context('llm.request.generate', sample_llm_message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Mock database operations
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            await process_llm_request(context)

            # Verify database interactions
            assert mock_db.add.called
            assert mock_db.commit.called
            mock_db.close.assert_called_once()

    async def test_process_llm_request_with_callback(
        self,
        task_context,
        sample_llm_message,
        mock_httpx_client,
        monkeypatch
    ):
        """Test LLM request processing with callback."""
        monkeypatch.setattr('httpx.AsyncClient', mock_httpx_client)

        # Add callback URL to message
        message = {**sample_llm_message, 'callback_url': 'http://example.com/callback'}
        context = task_context('llm.request.generate', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with patch('app.tasks.send_callback') as mock_callback:
                mock_callback.return_value = AsyncMock()

                await process_llm_request(context)

                # Verify callback was called
                assert mock_callback.called

    async def test_process_llm_request_http_error(
        self,
        task_context,
        sample_llm_message,
        monkeypatch
    ):
        """Test LLM request processing with HTTP error."""
        class MockFailedClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url, **kwargs):
                import httpx
                raise httpx.HTTPError("Connection failed")

        monkeypatch.setattr('httpx.AsyncClient', MockFailedClient)

        context = task_context('llm.request.generate', sample_llm_message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with pytest.raises(Exception):
                await process_llm_request(context)

    async def test_process_approval_create(
        self,
        task_context,
        sample_approval_message
    ):
        """Test approval creation."""
        context = task_context('approval.create', sample_approval_message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with patch('app.tasks.notify_approvers') as mock_notify:
                mock_notify.return_value = AsyncMock()

                await process_approval_create(context)

                # Verify database interactions
                assert mock_db.add.called
                assert mock_db.commit.called
                mock_db.close.assert_called_once()

                # Verify notification was sent
                assert mock_notify.called

    async def test_process_approval_create_no_approvers(
        self,
        task_context
    ):
        """Test approval creation without approvers."""
        message = {
            'request_id': 'approval_123',
            'user_id': 'user_456',
            'request_type': 'deployment',
            'request_data': {}
        }
        context = task_context('approval.create', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with patch('app.tasks.notify_approvers') as mock_notify:
                await process_approval_create(context)

                # Verify notification was not called
                assert not mock_notify.called

    async def test_process_approval_update(self, task_context):
        """Test approval update."""
        message = {
            'request_id': 'approval_123',
            'approver_id': 'approver_789',
            'status': 'approved',
            'comment': 'Looks good'
        }
        context = task_context('approval.update', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Mock approval record
            mock_approval = MagicMock()
            mock_approval.user_id = 'user_456'
            mock_db.query.return_value.filter.return_value.first.return_value = mock_approval

            with patch('app.tasks.notify_approval_decision') as mock_notify:
                mock_notify.return_value = AsyncMock()

                await process_approval_update(context)

                # Verify approval was updated
                assert mock_approval.status == 'approved'
                assert mock_approval.approver_id == 'approver_789'
                assert mock_approval.approval_comment == 'Looks good'

                # Verify commit was called
                assert mock_db.commit.called
                mock_db.close.assert_called_once()

                # Verify notification was sent
                assert mock_notify.called

    async def test_process_approval_update_not_found(self, task_context):
        """Test approval update when record not found."""
        message = {
            'request_id': 'nonexistent',
            'approver_id': 'approver_789',
            'status': 'approved',
            'comment': 'Looks good'
        }
        context = task_context('approval.update', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Mock no approval found
            mock_db.query.return_value.filter.return_value.first.return_value = None

            await process_approval_update(context)

            # Verify no commit was called
            assert not mock_db.commit.called

    async def test_process_email_notification(
        self,
        task_context,
        sample_notification_message,
        mock_smtp
    ):
        """Test email notification processing."""
        context = task_context('notification.email', sample_notification_message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with patch('app.tasks.send_email') as mock_send:
                mock_send.return_value = AsyncMock()

                await process_email_notification(context)

                # Verify email was sent
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][0] == sample_notification_message['recipient']
                assert call_args[0][1] == sample_notification_message['subject']
                assert call_args[0][2] == sample_notification_message['body']

                # Verify database interactions
                assert mock_db.add.called
                assert mock_db.commit.called
                mock_db.close.assert_called_once()

    async def test_process_email_notification_failure(
        self,
        task_context,
        sample_notification_message
    ):
        """Test email notification processing failure."""
        context = task_context('notification.email', sample_notification_message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            with patch('app.tasks.send_email') as mock_send:
                mock_send.side_effect = Exception("SMTP error")

                with pytest.raises(Exception):
                    await process_email_notification(context)

                # Verify error was logged to database
                assert mock_db.commit.called

    async def test_process_slack_notification_enabled(
        self,
        task_context,
        mock_httpx_client,
        monkeypatch
    ):
        """Test Slack notification when enabled."""
        # Enable Slack
        monkeypatch.setattr(settings, 'SLACK_ENABLED', True)
        monkeypatch.setattr(settings, 'SLACK_WEBHOOK_URL', 'http://slack.webhook.url')
        monkeypatch.setattr('httpx.AsyncClient', mock_httpx_client)

        message = {
            'notification_id': 'notif_123',
            'channel': '#general',
            'text': 'Test message'
        }
        context = task_context('notification.slack', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            await process_slack_notification(context)

            # Verify database interactions
            assert mock_db.add.called
            assert mock_db.commit.called
            mock_db.close.assert_called_once()

    async def test_process_slack_notification_disabled(
        self,
        task_context,
        monkeypatch
    ):
        """Test Slack notification when disabled."""
        # Disable Slack
        monkeypatch.setattr(settings, 'SLACK_ENABLED', False)

        message = {
            'notification_id': 'notif_123',
            'channel': '#general',
            'text': 'Test message'
        }
        context = task_context('notification.slack', message)

        with patch('app.tasks.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            await process_slack_notification(context)

            # Should return early without sending
            mock_db.close.assert_called_once()


class TestTaskRegistry:
    """Test TaskRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization with default handlers."""
        registry = TaskRegistry()

        assert 'llm_request' in registry.handlers
        assert 'approval_create' in registry.handlers
        assert 'approval_update' in registry.handlers
        assert 'notification_email' in registry.handlers
        assert 'notification_slack' in registry.handlers

    def test_get_handler_exists(self):
        """Test getting existing handler."""
        registry = TaskRegistry()
        handler = registry.get_handler('llm_request')
        assert handler is not None
        assert callable(handler)

    def test_get_handler_not_exists(self):
        """Test getting non-existent handler."""
        registry = TaskRegistry()
        handler = registry.get_handler('nonexistent')
        assert handler is None

    def test_register_new_handler(self):
        """Test registering new handler."""
        registry = TaskRegistry()

        async def custom_handler(context):
            pass

        registry.register('custom_task', custom_handler)

        handler = registry.get_handler('custom_task')
        assert handler is not None
        assert handler == custom_handler


@pytest.mark.asyncio
class TestHelperFunctions:
    """Test helper functions."""

    async def test_send_email(self, mock_smtp):
        """Test email sending."""
        from app.tasks import send_email

        await send_email(
            recipient='test@example.com',
            subject='Test Subject',
            body='Test body',
            html=False
        )

        # If no exception, test passed

    async def test_send_callback_success(self, mock_httpx_client, monkeypatch):
        """Test successful callback sending."""
        monkeypatch.setattr('httpx.AsyncClient', mock_httpx_client)

        from app.tasks import send_callback

        await send_callback(
            callback_url='http://example.com/callback',
            data={'status': 'completed'}
        )

        # If no exception, test passed

    async def test_notify_approvers(self, mock_smtp):
        """Test approver notification."""
        from app.tasks import notify_approvers

        with patch('app.tasks.send_email') as mock_send:
            mock_send.return_value = AsyncMock()

            approvers = ['approver1@example.com', 'approver2@example.com']
            await notify_approvers('req_123', 'deployment', approvers)

            # Verify email was sent to each approver
            assert mock_send.call_count == len(approvers)

    async def test_notify_approval_decision(self, mock_smtp):
        """Test approval decision notification."""
        from app.tasks import notify_approval_decision

        with patch('app.tasks.send_email') as mock_send:
            mock_send.return_value = AsyncMock()

            await notify_approval_decision(
                user_id='user@example.com',
                request_id='req_123',
                status='approved',
                comment='Looks good'
            )

            # Verify email was sent
            mock_send.assert_called_once()
