"""
Event Publisher - Publish events to RabbitMQ

This module provides an async interface to publish events to RabbitMQ.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType

logger = logging.getLogger(__name__)


class EventPublisherError(Exception):
    """Custom exception for event publisher errors"""
    pass


class EventPublisher:
    """Async RabbitMQ event publisher"""

    def __init__(
        self,
        host: str = "rabbitmq",
        port: int = 5672,
        user: str = "devops",
        password: str = "devops123",
        vhost: str = "devops",
        exchange: str = "agent_events"
    ):
        """
        Initialize event publisher

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
            exchange: Exchange name for publishing
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.exchange_name = exchange

        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None

        self._is_connected = False

        logger.info(f"Event publisher initialized: {host}:{port}/{vhost}")

    async def connect(self, max_retries: int = 10, retry_delay: int = 10):
        """
        Connect to RabbitMQ with retry logic

        Args:
            max_retries: Maximum connection attempts
            retry_delay: Delay between retries (seconds)

        Raises:
            EventPublisherError: If connection fails after all retries
        """
        for attempt in range(1, max_retries + 1):
            try:
                # Build connection URL
                connection_url = (
                    f"amqp://{self.user}:{self.password}@"
                    f"{self.host}:{self.port}/{self.vhost}"
                )

                logger.info(f"Connecting to RabbitMQ (attempt {attempt}/{max_retries})...")

                # Connect
                self.connection = await aio_pika.connect_robust(connection_url)

                # Create channel
                self.channel = await self.connection.channel()

                # Declare exchange (topic type for routing)
                self.exchange = await self.channel.declare_exchange(
                    name=self.exchange_name,
                    type=ExchangeType.TOPIC,
                    durable=True
                )

                self._is_connected = True
                logger.info(f"✓ Connected to RabbitMQ exchange: {self.exchange_name}")
                return

            except Exception as e:
                logger.error(f"RabbitMQ connection failed (attempt {attempt}/{max_retries}): {e}")

                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise EventPublisherError(
                        f"Failed to connect to RabbitMQ after {max_retries} attempts"
                    ) from e

    async def publish(
        self,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True
    ):
        """
        Publish an event to RabbitMQ

        Args:
            routing_key: Routing key for the message (e.g., 'monitoring.incident.detected')
            message: Event data as dictionary
            persistent: Make message persistent (survive broker restart)

        Raises:
            EventPublisherError: If not connected or publish fails

        Example:
            await publisher.publish(
                routing_key='monitoring.incident.detected',
                message={
                    'incident_id': '123',
                    'severity': 'high',
                    'data': {...}
                }
            )
        """
        if not self._is_connected:
            raise EventPublisherError("Not connected to RabbitMQ. Call connect() first.")

        try:
            # Serialize message to JSON
            message_body = json.dumps(message, default=str)

            # Create AMQP message
            amqp_message = Message(
                body=message_body.encode(),
                delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT,
                content_type="application/json"
            )

            # Publish to exchange
            await self.exchange.publish(
                message=amqp_message,
                routing_key=routing_key
            )

            logger.debug(f"Published event: {routing_key} | {message.get('event_type', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to publish message: {e}", exc_info=True)
            raise EventPublisherError(f"Failed to publish event: {str(e)}") from e

    async def disconnect(self):
        """
        Disconnect from RabbitMQ gracefully

        Example:
            await publisher.disconnect()
        """
        if self.connection and not self.connection.is_closed:
            try:
                await self.connection.close()
                self._is_connected = False
                logger.info("✓ Disconnected from RabbitMQ")
            except Exception as e:
                logger.error(f"Error disconnecting from RabbitMQ: {e}")

    def is_connected(self) -> bool:
        """
        Check if connected to RabbitMQ

        Returns:
            True if connected, False otherwise
        """
        return self._is_connected and self.connection and not self.connection.is_closed

    async def health_check(self) -> bool:
        """
        Check if RabbitMQ connection is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.is_connected():
                return False

            # Try to declare a temporary queue as health check
            channel = await self.connection.channel()
            queue = await channel.declare_queue(
                name="",
                exclusive=True,
                auto_delete=True
            )
            await queue.delete()
            await channel.close()

            logger.debug("RabbitMQ health check: OK")
            return True

        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


async def example_usage():
    """Example usage of EventPublisher"""

    # Initialize publisher
    publisher = EventPublisher(
        host="localhost",
        user="devops",
        password="devops123"
    )

    try:
        # Connect
        await publisher.connect()

        # Publish event
        event = {
            "incident_id": "inc-12345",
            "agent": "monitoring",
            "event_type": "incident_detected",
            "severity": "high",
            "data": {
                "metric": "cpu_usage",
                "value": 95.0,
                "threshold": 80.0
            }
        }

        await publisher.publish(
            routing_key="monitoring.incident.detected",
            message=event
        )

        logger.info("Event published successfully!")

    finally:
        # Disconnect
        await publisher.disconnect()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run example
    asyncio.run(example_usage())
