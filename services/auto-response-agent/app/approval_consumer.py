"""
Approval Decision Consumer Module

Consumes approval decision events (approved/rejected) from approval dashboard
and triggers action execution or cancellation.
"""
import logging
import json
import asyncio
from typing import Dict, Any, Callable, Optional
import aio_pika
from aio_pika import ExchangeType

logger = logging.getLogger(__name__)


class ApprovalConsumer:
    """Consume approval decision events from RabbitMQ"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        vhost: str,
        exchange: str,
        queue_name: str = "auto_response_approval_queue"
    ):
        """
        Initialize approval consumer

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
            exchange: Exchange name
            queue_name: Queue name for approval decisions
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.exchange_name = exchange
        self.queue_name = queue_name

        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self.queue: Optional[aio_pika.Queue] = None

        self.message_handler: Optional[Callable] = None

    async def connect(self):
        """Connect to RabbitMQ and setup exchange/queue for approval decisions"""
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

            # Declare exchange (same exchange as approval dashboard publishes to)
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

            # Bind queue to BOTH approval.approved and approval.rejected routing keys
            await self.queue.bind(self.exchange, routing_key="approval.approved")
            await self.queue.bind(self.exchange, routing_key="approval.rejected")

            logger.info(
                f"✓ Approval consumer connected to RabbitMQ "
                f"(exchange: {self.exchange_name}, listening for approval.approved & approval.rejected)"
            )

        except Exception as e:
            logger.error(f"Failed to connect approval consumer to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("✓ Approval consumer disconnected from RabbitMQ")

    def set_message_handler(self, handler: Callable):
        """
        Set the message handler callback

        Args:
            handler: Async function to handle approval decision messages
                     Signature: async def handler(decision_event: Dict[str, Any])
        """
        self.message_handler = handler

    async def start_consuming(self):
        """Start consuming approval decision messages"""
        if not self.message_handler:
            raise RuntimeError("Message handler not set. Call set_message_handler() first.")

        if not self.queue:
            raise RuntimeError("Not connected. Call connect() first.")

        logger.info(f"Starting to consume approval decisions from {self.queue_name}...")

        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await self._process_message(message)

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process a single approval decision message"""
        try:
            # Decode message body
            body = message.body.decode()
            event = json.loads(body)

            approval_id = event.get("approval_id")
            decision = event.get("decision")  # 'approved' or 'rejected'

            logger.info(
                f"Received approval decision: ID={approval_id}, Decision={decision}"
            )

            # Call handler
            await self.message_handler(event)

            logger.debug(f"Successfully processed approval decision: {approval_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode approval message: {e}")
        except Exception as e:
            logger.error(f"Error processing approval decision: {e}", exc_info=True)
