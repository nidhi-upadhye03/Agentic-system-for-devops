"""
Event Publisher Module

Publishes action execution results to RabbitMQ.
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import aio_pika
from aio_pika import ExchangeType, DeliveryMode

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publish events to RabbitMQ"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        vhost: str,
        exchange: str
    ):
        """
        Initialize event publisher

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            user: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
            exchange: Exchange name
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

    async def connect(self):
        """Connect to RabbitMQ and setup exchange"""
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

            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True
            )

            logger.info(f"✓ Event publisher connected to RabbitMQ (exchange: {self.exchange_name})")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        if self.connection:
            await self.connection.close()
            logger.info("✓ Event publisher disconnected from RabbitMQ")

    async def publish_action_executed(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        execution_result: Dict[str, Any],
        status: str,
        approval_id: Optional[str] = None,
        error: Optional[str] = None,
        routing_key: str = "autoresponse.action.executed"
    ):
        """
        Publish action execution result

        Args:
            incident_id: Associated incident ID
            action_type: Type of action executed
            action_details: Full action details
            execution_result: Result from K8s executor
            status: Execution status (success, failed, approved, rejected, timeout)
            approval_id: Approval request ID if approval was required
            error: Error message if execution failed
            routing_key: Routing key for event
        """
        event = {
            "event_type": "action_executed",
            "event_id": f"action_{incident_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "action": {
                "type": action_type,
                "details": action_details,
                "status": status
            },
            "execution_result": execution_result
        }

        if approval_id:
            event["approval_id"] = approval_id

        if error:
            event["error"] = error

        await self._publish_event(event, routing_key)

        logger.info(
            f"Published action_executed event: {action_type} on "
            f"{action_details.get('target', 'unknown')} ({status})"
        )

    async def publish_action_pending_approval(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        approval_id: str,
        validation_result: Dict[str, Any],
        routing_key: str = "autoresponse.action.pending"
    ):
        """
        Publish action pending approval notification

        Args:
            incident_id: Associated incident ID
            action_type: Type of action
            action_details: Full action details
            approval_id: Approval request ID
            validation_result: Validation results
            routing_key: Routing key for event
        """
        event = {
            "event_type": "action_pending_approval",
            "event_id": f"pending_{incident_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "approval_id": approval_id,
            "action": {
                "type": action_type,
                "details": action_details
            },
            "validation": validation_result
        }

        await self._publish_event(event, routing_key)

        logger.info(f"Published action_pending_approval event: {approval_id}")

    async def publish_action_validation_failed(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        validation_result: Dict[str, Any],
        routing_key: str = "autoresponse.action.validation_failed"
    ):
        """
        Publish action validation failure

        Args:
            incident_id: Associated incident ID
            action_type: Type of action
            action_details: Full action details
            validation_result: Validation results with failure reasons
            routing_key: Routing key for event
        """
        event = {
            "event_type": "action_validation_failed",
            "event_id": f"validation_failed_{incident_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "action": {
                "type": action_type,
                "details": action_details
            },
            "validation": validation_result
        }

        await self._publish_event(event, routing_key)

        logger.warning(
            f"Published action_validation_failed event: {action_type} "
            f"(reasons: {validation_result.get('failure_reasons', [])})"
        )

    async def publish_auto_execution_triggered(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        validation_result: Dict[str, Any],
        routing_key: str = "autoresponse.action.auto_executing"
    ):
        """
        Publish auto-execution notification

        Args:
            incident_id: Associated incident ID
            action_type: Type of action
            action_details: Full action details
            validation_result: Validation results showing auto-execute decision
            routing_key: Routing key for event
        """
        event = {
            "event_type": "auto_execution_triggered",
            "event_id": f"auto_exec_{incident_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident_id,
            "action": {
                "type": action_type,
                "details": action_details
            },
            "validation": validation_result
        }

        await self._publish_event(event, routing_key)

        logger.info(f"Published auto_execution_triggered event: {action_type}")

    async def _publish_event(
        self,
        event: Dict[str, Any],
        routing_key: str
    ):
        """
        Publish event to exchange

        Args:
            event: Event payload
            routing_key: Routing key
        """
        if not self.exchange:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Convert event to JSON
            message_body = json.dumps(event, indent=2)

            # Create message
            message = aio_pika.Message(
                body=message_body.encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                timestamp=datetime.utcnow()
            )

            # Publish to exchange
            await self.exchange.publish(
                message,
                routing_key=routing_key
            )

            logger.debug(f"Published event: {event['event_type']} -> {routing_key}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if publisher is healthy

        Returns:
            True if connected and ready
        """
        return (
            self.connection is not None and
            not self.connection.is_closed and
            self.channel is not None and
            not self.channel.is_closed
        )
