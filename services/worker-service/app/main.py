"""
Worker Service Entry Point
Handles RabbitMQ connection, message consumption, and graceful shutdown
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
import pika
from pika.adapters.asyncio_connection import AsyncioConnection
from pika.channel import Channel

from app.consumers import MessageConsumer
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class WorkerService:
    """Main worker service class handling RabbitMQ connection and consumers."""

    def __init__(self):
        self.connection: Optional[AsyncioConnection] = None
        self.channel: Optional[Channel] = None
        self.consumer: Optional[MessageConsumer] = None
        self.should_stop = False
        self.loop = asyncio.get_event_loop()

    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.should_stop = True
            if self.connection and not self.connection.is_closed:
                self.connection.close()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def on_connection_open(self, connection):
        """Callback when connection is opened."""
        logger.info("RabbitMQ connection established")
        self.connection = connection
        self.connection.channel(on_open_callback=self.on_channel_open)

    def on_connection_open_error(self, connection, error):
        """Callback when connection fails to open."""
        logger.error(f"Failed to open RabbitMQ connection: {error}")
        self.reconnect()

    def on_connection_closed(self, connection, reason):
        """Callback when connection is closed."""
        logger.warning(f"RabbitMQ connection closed: {reason}")
        if not self.should_stop:
            self.reconnect()

    def on_channel_open(self, channel):
        """Callback when channel is opened."""
        logger.info("RabbitMQ channel opened")
        self.channel = channel
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.setup_exchanges_and_queues()

    def on_channel_closed(self, channel, reason):
        """Callback when channel is closed."""
        logger.warning(f"RabbitMQ channel closed: {reason}")
        if not self.should_stop and self.connection and not self.connection.is_closed:
            self.connection.close()

    def setup_exchanges_and_queues(self):
        """Declare exchanges, queues, and bindings."""
        # Declare exchanges
        self.channel.exchange_declare(
            exchange=settings.RABBITMQ_EXCHANGE,
            exchange_type='topic',
            durable=True,
            callback=self.on_exchange_declared
        )

    def on_exchange_declared(self, frame):
        """Callback when exchange is declared."""
        logger.info(f"Exchange '{settings.RABBITMQ_EXCHANGE}' declared")

        # Declare queues
        queues = [
            settings.QUEUE_LLM_REQUESTS,
            settings.QUEUE_APPROVALS,
            settings.QUEUE_NOTIFICATIONS,
            settings.QUEUE_DEAD_LETTER
        ]

        for queue in queues:
            self.channel.queue_declare(
                queue=queue,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': settings.RABBITMQ_EXCHANGE,
                    'x-dead-letter-routing-key': f"dead_letter.{queue}",
                    'x-message-ttl': 86400000  # 24 hours
                }
            )

        # Bind queues to exchange
        self.channel.queue_bind(
            queue=settings.QUEUE_LLM_REQUESTS,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key='llm.request.*'
        )

        self.channel.queue_bind(
            queue=settings.QUEUE_APPROVALS,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key='approval.*'
        )

        self.channel.queue_bind(
            queue=settings.QUEUE_NOTIFICATIONS,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key='notification.*'
        )

        self.channel.queue_bind(
            queue=settings.QUEUE_DEAD_LETTER,
            exchange=settings.RABBITMQ_EXCHANGE,
            routing_key='dead_letter.*'
        )

        logger.info("Queues declared and bound")
        self.start_consuming()

    def start_consuming(self):
        """Start consuming messages from queues."""
        logger.info("Starting message consumers...")

        # Set QoS
        self.channel.basic_qos(prefetch_count=settings.WORKER_PREFETCH_COUNT)

        # Create consumer
        self.consumer = MessageConsumer(self.channel, self.loop)

        # Start consuming from each queue
        self.consumer.consume(settings.QUEUE_LLM_REQUESTS)
        self.consumer.consume(settings.QUEUE_APPROVALS)
        self.consumer.consume(settings.QUEUE_NOTIFICATIONS)

        logger.info("All consumers started successfully")

    def reconnect(self):
        """Reconnect to RabbitMQ after a delay."""
        if self.should_stop:
            return

        logger.info(f"Reconnecting to RabbitMQ in {settings.RABBITMQ_RECONNECT_DELAY} seconds...")
        self.loop.call_later(settings.RABBITMQ_RECONNECT_DELAY, self.connect)

    def connect(self):
        """Connect to RabbitMQ."""
        logger.info(f"Connecting to RabbitMQ at {settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}")

        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )

        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            virtual_host=settings.RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        self.connection = AsyncioConnection(
            parameters=parameters,
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed
        )

    def run(self):
        """Run the worker service."""
        logger.info("Starting Worker Service...")
        self.setup_signal_handlers()

        try:
            self.connect()
            self.loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            logger.info("Shutting down Worker Service...")
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            self.loop.close()
            logger.info("Worker Service stopped")


def main():
    """Main entry point."""
    try:
        service = WorkerService()
        service.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
