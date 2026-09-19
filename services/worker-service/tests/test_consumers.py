"""
Unit tests for message consumers
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pika.spec import Basic

from app.consumers import MessageConsumer
from app.tasks import TaskContext
from app.config import settings


@pytest.mark.asyncio
class TestMessageConsumer:
    """Test MessageConsumer class."""

    def test_consumer_initialization(self, mock_channel):
        """Test consumer initialization."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        assert consumer.channel == mock_channel
        assert consumer.loop == loop
        assert consumer.task_registry is not None

    def test_consume_starts_consuming(self, mock_channel):
        """Test that consume starts message consumption."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        queue_name = "test_queue"
        consumer.consume(queue_name)

        mock_channel.basic_consume.assert_called_once()
        call_args = mock_channel.basic_consume.call_args
        assert call_args[1]['queue'] == queue_name

    def test_parse_message_valid_json(self, mock_channel):
        """Test parsing valid JSON message."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        test_data = {'key': 'value', 'number': 123}
        body = json.dumps(test_data).encode('utf-8')

        result = consumer._parse_message(body)
        assert result == test_data

    def test_parse_message_invalid_json(self, mock_channel):
        """Test parsing invalid JSON message."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        body = b'invalid json {'
        result = consumer._parse_message(body)
        assert result is None

    def test_get_retry_count_from_headers(self, mock_channel, mock_properties):
        """Test extracting retry count from message headers."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        mock_properties.headers = {'x-retry-count': 3}
        retry_count = consumer._get_retry_count(mock_properties)
        assert retry_count == 3

    def test_get_retry_count_no_headers(self, mock_channel, mock_properties):
        """Test default retry count when no headers present."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        mock_properties.headers = None
        retry_count = consumer._get_retry_count(mock_properties)
        assert retry_count == 0

    def test_extract_task_type_from_message(self, mock_channel):
        """Test extracting task type from message."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        message = {'task_type': 'llm_request'}
        task_type = consumer._extract_task_type('llm.request.generate', message)
        assert task_type == 'llm_request'

    def test_extract_task_type_from_routing_key(self, mock_channel):
        """Test extracting task type from routing key."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        message = {}
        task_type = consumer._extract_task_type('approval.create', message)
        assert task_type == 'approval_create'

    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_channel, task_context, sample_llm_message):
        """Test successful message processing."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message)

        # Mock task handler
        async def mock_handler(ctx):
            return True

        consumer.task_registry.handlers['llm_request'] = mock_handler

        result = await consumer._process_message(context)
        assert result is True

    @pytest.mark.asyncio
    async def test_process_message_no_handler(self, mock_channel, task_context):
        """Test message processing with no handler."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('unknown.task', {})
        result = await consumer._process_message(context)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_message_handler_exception(self, mock_channel, task_context, sample_llm_message):
        """Test message processing with handler exception."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message)

        # Mock task handler that raises exception
        async def mock_handler(ctx):
            raise ValueError("Test error")

        consumer.task_registry.handlers['llm_request'] = mock_handler

        result = await consumer._process_message(context)
        assert result is False

    def test_acknowledge_message(self, mock_channel):
        """Test message acknowledgment."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        delivery_tag = 123
        consumer._acknowledge_message(mock_channel, delivery_tag)

        mock_channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)

    def test_reject_message_no_requeue(self, mock_channel):
        """Test message rejection without requeue."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        delivery_tag = 123
        consumer._reject_message(mock_channel, delivery_tag, requeue=False)

        mock_channel.basic_nack.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=False
        )

    def test_reject_message_with_requeue(self, mock_channel):
        """Test message rejection with requeue."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        delivery_tag = 123
        consumer._reject_message(mock_channel, delivery_tag, requeue=True)

        mock_channel.basic_nack.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=True
        )

    @pytest.mark.asyncio
    async def test_handle_failure_retry(self, mock_channel, task_context, sample_llm_message):
        """Test failure handling with retry."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message, retry_count=0)

        with patch.object(consumer, '_requeue_with_retry') as mock_requeue:
            await consumer._handle_failure(mock_channel, 123, context)
            mock_requeue.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_failure_max_retries(self, mock_channel, task_context, sample_llm_message):
        """Test failure handling when max retries exceeded."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message, retry_count=settings.MAX_RETRIES)

        with patch.object(consumer, '_send_to_dead_letter') as mock_dead_letter:
            await consumer._handle_failure(mock_channel, 123, context)
            mock_dead_letter.assert_called_once()

    def test_requeue_with_retry(self, mock_channel, task_context, sample_llm_message):
        """Test message requeuing with updated retry count."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message)
        delivery_tag = 123
        retry_count = 1

        consumer._requeue_with_retry(mock_channel, delivery_tag, context, retry_count)

        # Verify message was republished
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args

        assert call_args[1]['exchange'] == settings.RABBITMQ_EXCHANGE
        assert call_args[1]['routing_key'] == context.routing_key

        # Verify retry count was updated
        properties = call_args[1]['properties']
        assert properties.headers['x-retry-count'] == retry_count

        # Verify original message was acknowledged
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)

    def test_send_to_dead_letter(self, mock_channel, task_context, sample_llm_message):
        """Test sending message to dead letter queue."""
        loop = asyncio.get_event_loop()
        consumer = MessageConsumer(mock_channel, loop)

        context = task_context('llm.request.generate', sample_llm_message, retry_count=3)
        delivery_tag = 123

        consumer._send_to_dead_letter(mock_channel, delivery_tag, context)

        # Verify message was published to dead letter queue
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args

        assert call_args[1]['exchange'] == settings.RABBITMQ_EXCHANGE
        assert call_args[1]['routing_key'] == f"dead_letter.{context.routing_key}"

        # Verify message contains failure metadata
        body = call_args[1]['body']
        message_data = json.loads(body.decode('utf-8'))
        assert 'failure_reason' in message_data
        assert message_data['retry_count'] == 3

        # Verify original message was acknowledged
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)
