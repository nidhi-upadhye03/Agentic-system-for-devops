"""
Event Consumer - Consume events from RabbitMQ

Listens for incident events and triggers analysis.
"""
import asyncio
import json
import logging
from typing import Callable, Optional
import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)


class EventConsumerError(Exception):
    """Custom exception for event consumer errors"""
    pass


class EventConsumer:
    """Async RabbitMQ event consumer"""

    def __init__(
        self,
        host: str = "rabbitmq",
        port: int = 5672,
        user: str = "devops",
        password: str = "devops123",
        vhost: str = "devops"
    ):
        """
        Initialize event consumer

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost

        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

        logger.info(f"Event consumer initialized: {host}:{port}/{vhost}")

    async def connect(self, max_retries: int = 5, retry_delay: int = 5):
        """
        Connect to RabbitMQ with retry logic

        Args:
            max_retries: Maximum connection attempts
            retry_delay: Delay between retries (seconds)

        Raises:
            EventConsumerError: If connection fails after all retries
        """
        for attempt in range(1, max_retries + 1):
            try:
                connection_url = (
                    f"amqp://{self.user}:{self.password}@"
                    f"{self.host}:{self.port}/{self.vhost}"
                )

                logger.info(f"Connecting to RabbitMQ (attempt {attempt}/{max_retries})...")

                self.connection = await aio_pika.connect_robust(connection_url)
                self.channel = await self.connection.channel()

                await self.channel.set_qos(prefetch_count=1)

                logger.info(f"✓ Connected to RabbitMQ")
                return

            except Exception as e:
                logger.error(f"RabbitMQ connection failed (attempt {attempt}/{max_retries}): {e}")

                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise EventConsumerError(
                        f"Failed to connect to RabbitMQ after {max_retries} attempts"
                    ) from e

    async def subscribe(
        self,
        exchange: str,
        routing_key: str,
        callback: Callable,
        queue_name: str = ""
    ):
        """
        Subscribe to events with a routing key

        Args:
            exchange: Exchange name
            routing_key: Routing key pattern (e.g., "monitoring.incident.*")
            callback: Async callback function to handle messages
            queue_name: Queue name (auto-generated if empty)

        Raises:
            EventConsumerError: If subscription fails
        """
        if not self.channel:
            raise EventConsumerError("Not connected to RabbitMQ. Call connect() first.")

        try:
            # Declare exchange
            exchange_obj = await self.channel.declare_exchange(
                name=exchange,
                type=ExchangeType.TOPIC,
                durable=True
            )

            # Declare queue (exclusive if no name provided)
            queue = await self.channel.declare_queue(
                name=queue_name,
                exclusive=not bool(queue_name),
                auto_delete=not bool(queue_name)
            )

            # Bind queue to exchange with routing key
            await queue.bind(exchange_obj, routing_key=routing_key)

            logger.info(f"✓ Subscribed to {exchange} with routing key: {routing_key}")

            # Start consuming
            async def on_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        # Parse message
                        event = json.loads(message.body.decode())
                        logger.debug(f"Received event: {event.get('type', 'unknown')}")

                        # Call callback
                        await callback(event)

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)

            await queue.consume(on_message)

        except Exception as e:
            raise EventConsumerError(f"Failed to subscribe: {str(e)}") from e

    async def disconnect(self):
        """Disconnect from RabbitMQ gracefully"""
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                logger.info("✓ Disconnected from RabbitMQ")
            except Exception as e:
                logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
