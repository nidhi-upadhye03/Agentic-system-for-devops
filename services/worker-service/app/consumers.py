"""
RabbitMQ Message Consumer
Handles message consumption with error handling and retry logic
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from pika.channel import Channel
from pika.spec import Basic, BasicProperties

from app.config import settings
from app.tasks import TaskRegistry, TaskContext

logger = logging.getLogger(__name__)


class MessageConsumer:
    """Message consumer with error handling and retry logic."""

    def __init__(self, channel: Channel, loop: asyncio.AbstractEventLoop):
        self.channel = channel
        self.loop = loop
        self.task_registry = TaskRegistry()

    def consume(self, queue_name: str):
        """Start consuming messages from a queue."""
        logger.info(f"Starting consumer for queue: {queue_name}")
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=self._on_message_wrapper
        )

    def _on_message_wrapper(
        self,
        channel: Channel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Wrapper to handle message in asyncio."""
        asyncio.run_coroutine_threadsafe(
            self._handle_message(channel, method, properties, body),
            self.loop
        )

    async def _handle_message(
        self,
        channel: Channel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes
    ):
        """Handle incoming message with error handling and retries."""
        delivery_tag = method.delivery_tag
        routing_key = method.routing_key

        try:
            # Parse message
            message = self._parse_message(body)
            if message is None:
                logger.error(f"Failed to parse message from {routing_key}")
                self._reject_message(channel, delivery_tag, requeue=False)
                return

            logger.info(f"Processing message from {routing_key}: {message.get('task_id', 'unknown')}")

            # Get retry count
            retry_count = self._get_retry_count(properties)

            # Create task context
            context = TaskContext(
                routing_key=routing_key,
                message=message,
                retry_count=retry_count,
                properties=properties
            )

            # Process message
            success = await self._process_message(context)

            if success:
                # Acknowledge message
                self._acknowledge_message(channel, delivery_tag)
                logger.info(f"Message processed successfully: {message.get('task_id', 'unknown')}")
            else:
                # Handle failure with retry logic
                await self._handle_failure(channel, delivery_tag, context)

        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            self._reject_message(channel, delivery_tag, requeue=True)

    def _parse_message(self, body: bytes) -> Optional[Dict[str, Any]]:
        """Parse message body as JSON."""
        try:
            return json.loads(body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse message: {e}")
            return None

    def _get_retry_count(self, properties: BasicProperties) -> int:
        """Extract retry count from message headers."""
        if properties.headers and 'x-retry-count' in properties.headers:
            return int(properties.headers['x-retry-count'])
        return 0

    async def _process_message(self, context: TaskContext) -> bool:
        """Process message by routing to appropriate task handler."""
        try:
            # Get task type from routing key or message
            task_type = self._extract_task_type(context.routing_key, context.message)

            # Get task handler
            handler = self.task_registry.get_handler(task_type)
            if handler is None:
                logger.error(f"No handler found for task type: {task_type}")
                return False

            # Execute task
            await handler(context)
            return True

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return False

    def _extract_task_type(self, routing_key: str, message: Dict[str, Any]) -> str:
        """Extract task type from routing key or message."""
        # Try to get from message first
        if 'task_type' in message:
            return message['task_type']

        # Extract from routing key (e.g., "llm.request.generate" -> "llm_request")
        parts = routing_key.split('.')
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"

        return routing_key

    async def _handle_failure(
        self,
        channel: Channel,
        delivery_tag: int,
        context: TaskContext
    ):
        """Handle message processing failure with retry logic."""
        if context.retry_count < settings.MAX_RETRIES:
            # Retry with delay
            retry_count = context.retry_count + 1
            logger.warning(
                f"Message processing failed, scheduling retry {retry_count}/{settings.MAX_RETRIES}"
            )

            # Requeue with updated retry count
            await asyncio.sleep(settings.RETRY_DELAY)
            self._requeue_with_retry(channel, delivery_tag, context, retry_count)
        else:
            # Max retries exceeded, send to dead letter queue
            logger.error(
                f"Max retries exceeded for message: {context.message.get('task_id', 'unknown')}"
            )
            self._send_to_dead_letter(channel, delivery_tag, context)

    def _requeue_with_retry(
        self,
        channel: Channel,
        delivery_tag: int,
        context: TaskContext,
        retry_count: int
    ):
        """Requeue message with updated retry count."""
        try:
            # Update retry count in headers
            headers = dict(context.properties.headers) if context.properties.headers else {}
            headers['x-retry-count'] = retry_count

            # Republish message
            channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=context.routing_key,
                body=json.dumps(context.message).encode('utf-8'),
                properties=BasicProperties(
                    delivery_mode=2,  # Persistent
                    headers=headers
                )
            )

            # Acknowledge original message
            self._acknowledge_message(channel, delivery_tag)

        except Exception as e:
            logger.error(f"Failed to requeue message: {e}", exc_info=True)
            self._reject_message(channel, delivery_tag, requeue=True)

    def _send_to_dead_letter(
        self,
        channel: Channel,
        delivery_tag: int,
        context: TaskContext
    ):
        """Send message to dead letter queue."""
        try:
            # Add failure metadata
            dead_letter_message = {
                **context.message,
                'failure_reason': 'Max retries exceeded',
                'retry_count': context.retry_count,
                'original_routing_key': context.routing_key
            }

            # Publish to dead letter queue
            channel.basic_publish(
                exchange=settings.RABBITMQ_EXCHANGE,
                routing_key=f"dead_letter.{context.routing_key}",
                body=json.dumps(dead_letter_message).encode('utf-8'),
                properties=BasicProperties(delivery_mode=2)
            )

            # Acknowledge original message
            self._acknowledge_message(channel, delivery_tag)

        except Exception as e:
            logger.error(f"Failed to send to dead letter queue: {e}", exc_info=True)
            self._reject_message(channel, delivery_tag, requeue=False)

    def _acknowledge_message(self, channel: Channel, delivery_tag: int):
        """Acknowledge message."""
        try:
            channel.basic_ack(delivery_tag=delivery_tag)
        except Exception as e:
            logger.error(f"Failed to acknowledge message: {e}", exc_info=True)

    def _reject_message(self, channel: Channel, delivery_tag: int, requeue: bool = False):
        """Reject message."""
        try:
            channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
        except Exception as e:
            logger.error(f"Failed to reject message: {e}", exc_info=True)
