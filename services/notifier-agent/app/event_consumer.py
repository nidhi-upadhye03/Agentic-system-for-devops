"""
Event Consumer Module

Consumes all agent events from RabbitMQ for notification.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Callable, Optional, List
import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)


class EventConsumer:
    """Consume agent events from RabbitMQ"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        vhost: str,
        exchange: str,
        routing_keys: List[str],
        queue_name: str = "notifier_queue"
    ):
        """
        Initialize event consumer

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
            exchange: Exchange name
            routing_keys: List of routing keys to bind to
            queue_name: Queue name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.exchange_name = exchange
        self.routing_keys = routing_keys
        self.queue_name = queue_name

        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.queue: Optional[aio_pika.Queue] = None

        self.message_handler: Optional[Callable] = None

    async def connect(self):
        """Connect to RabbitMQ and setup exchange/queue"""
        try:
            # Connect to RabbitMQ
            self.connection = await aio_pika.connect_robust(
                host=self.host,
                port=self.port,
                login=self.user,
                password=self.password,
                virtualhost=self.vhost
            )

            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)  # Process up to 10 messages concurrently

            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )

            # Declare queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True
            )

            # Bind queue to exchange with multiple routing keys
            for routing_key in self.routing_keys:
                await self.queue.bind(self.exchange, routing_key=routing_key)
                logger.info(f"Bound queue to routing key: {routing_key}")

            logger.info(
                f"✓ Event consumer connected to RabbitMQ "
                f"(exchange: {self.exchange_name}, keys: {len(self.routing_keys)})"
            )

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("✓ Event consumer disconnected from RabbitMQ")

    def set_message_handler(self, handler: Callable):
        """
        Set the message handler callback

        Args:
            handler: Async function to handle messages
                     Signature: async def handler(event: Dict[str, Any])
        """
        self.message_handler = handler

    async def start_consuming(self):
        """Start consuming messages"""
        if not self.message_handler:
            raise RuntimeError("Message handler not set. Call set_message_handler() first.")

        if not self.queue:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.info(f"Starting to consume messages from {self.queue_name}...")

        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await self._process_message(message)

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process a single message"""
        try:
            # Decode message body
            body = message.body.decode()
            event = json.loads(body)

            event_type = event.get("event_type", "unknown")
            routing_key = message.routing_key

            logger.info(f"Received event: {event_type} (routing_key: {routing_key})")

            # Call handler
            await self.message_handler(event)

            logger.debug(f"Successfully processed event: {event.get('event_id', 'N/A')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
