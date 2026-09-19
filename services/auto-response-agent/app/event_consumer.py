"""
Event Consumer Module

Consumes analysis events from RabbitMQ and triggers auto-response workflow.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Callable, Optional
import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)


class EventConsumer:
    """Consume events from RabbitMQ"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        vhost: str,
        exchange: str,
        routing_key: str,
        queue_name: str = "auto_response_queue"
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
            routing_key: Routing key to bind to
            queue_name: Queue name
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.exchange_name = exchange
        self.routing_key = routing_key
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
            await self.channel.set_qos(prefetch_count=1)

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

            # Bind queue to exchange with routing key
            await self.queue.bind(self.exchange, routing_key=self.routing_key)

            logger.info(
                f"✓ Event consumer connected to RabbitMQ "
                f"(exchange: {self.exchange_name}, routing_key: {self.routing_key})"
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

            logger.info(
                f"Received event: {event.get('event_type', 'unknown')} "
                f"(incident: {event.get('incident_id', 'N/A')})"
            )

            # Call handler
            await self.message_handler(event)

            logger.debug(f"Successfully processed event: {event.get('event_id', 'N/A')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    async def consume_one(self, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Consume a single message (for testing)

        Args:
            timeout: Timeout in seconds

        Returns:
            Event dict or None if timeout
        """
        if not self.queue:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            message = await asyncio.wait_for(
                self.queue.get(timeout=timeout),
                timeout=timeout
            )

            if message:
                async with message.process():
                    body = message.body.decode()
                    event = json.loads(body)
                    return event

        except asyncio.TimeoutError:
            logger.warning(f"No message received within {timeout} seconds")
            return None
        except Exception as e:
            logger.error(f"Error consuming message: {e}")
            return None
