"""
Notifier Agent - Main Orchestrator

Autonomous notification agent that:
1. Consumes all agent events from RabbitMQ
2. Formats rich Slack messages
3. Sends notifications to configured channels
"""
import logging
import asyncio
import signal
from typing import Dict, Any
from datetime import datetime

from app.config import config
from app.slack_client import SlackClient
from app.email_client import EmailClient
from app.sms_client import SMSClient
from app.pagerduty_client import PagerDutyClient
from app.event_consumer import EventConsumer

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotifierAgent:
    """Main notifier agent orchestrator"""

    def __init__(self):
        """Initialize agent with all components"""
        logger.info(f"Initializing Notifier Agent v{config.agent_version}")

        # Initialize Slack client
        self.slack_client = SlackClient(
            bot_token=config.slack_token,  # Changed from slack_bot_token
            channel=config.slack_channel,
            username=config.slack_username,
            icon_emoji=config.slack_icon_emoji,
            timeout=config.slack_timeout
        )

        # Initialize Email client
        self.email_client = EmailClient(
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            from_email=config.from_email,
            enabled=config.email_enabled
        )

        # Initialize SMS client
        self.sms_client = SMSClient(
            account_sid=config.twilio_account_sid,
            auth_token=config.twilio_auth_token,
            from_number=config.twilio_from_number,
            enabled=config.sms_enabled
        )

        # Initialize PagerDuty client
        self.pagerduty_client = PagerDutyClient(
            integration_key=config.pagerduty_integration_key,
            enabled=config.pagerduty_enabled
        )

        # Parse recipient lists
        self.email_recipients = [e.strip() for e in config.email_recipients.split(',') if e.strip()]
        self.sms_recipients = [p.strip() for p in config.sms_recipients.split(',') if p.strip()]

        # Build routing keys list
        routing_keys = []
        if config.notify_incidents:
            routing_keys.append(config.rabbitmq_incident_routing_key)
        if config.notify_analysis:
            routing_keys.append(config.rabbitmq_analysis_routing_key)
        if config.notify_actions:
            routing_keys.append(config.rabbitmq_action_routing_key)
        if config.notify_approvals:
            routing_keys.append(config.rabbitmq_approval_routing_key)

        # Initialize event consumer
        self.event_consumer = EventConsumer(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange,
            routing_keys=routing_keys,
            queue_name="notifier_queue"
        )

        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the agent"""
        logger.info("=" * 60)
        logger.info(f"Starting Notifier Agent v{config.agent_version}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Slack Channel: {config.slack_channel}")
        logger.info(f"Email Enabled: {self.email_client.is_enabled()} ({len(self.email_recipients)} recipients)")
        logger.info(f"SMS Enabled: {self.sms_client.is_enabled()} ({len(self.sms_recipients)} recipients)")
        logger.info(f"PagerDuty Enabled: {self.pagerduty_client.is_enabled()}")
        logger.info("=" * 60)

        try:
            # Connect to services
            await self._connect_services()

            # Setup message handler
            self.event_consumer.set_message_handler(self.on_agent_event)

            # Start consuming events
            self.running = True
            logger.info("✓ Notifier Agent is ready and listening for events")

            # Start consuming in background
            consume_task = asyncio.create_task(self.event_consumer.start_consuming())

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Cancel consuming task
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"Failed to start agent: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the agent gracefully"""
        logger.info("Stopping Notifier Agent...")
        self.running = False

        try:
            await self.event_consumer.disconnect()
            logger.info("✓ Notifier Agent stopped gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def _connect_services(self):
        """Connect to all external services"""
        logger.info("Connecting to services...")

        # Connect RabbitMQ consumer
        await self.event_consumer.connect()

        # Connect Slack client
        slack_ok = await self.slack_client.connect()
        if not slack_ok:
            logger.warning("Slack connection failed - notifications will be skipped")

        logger.info("✓ All services connected")

    async def on_agent_event(self, event: Dict[str, Any]):
        """
        Handle agent event

        Args:
            event: Agent event with type and payload
        """
        event_type = event.get("event_type", "unknown")

        logger.info(f"Processing event: {event_type}")

        try:
            # Check severity filter
            if not self._should_notify(event):
                logger.info(f"Event filtered out based on severity/settings")
                return

            # Route to appropriate handler
            if event_type == "incident_detected":
                await self.handle_incident_detected(event)

            elif event_type == "analysis_complete":
                await self.handle_analysis_complete(event)

            elif event_type == "action_executed":
                await self.handle_action_executed(event)

            elif event_type == "action_pending_approval":
                await self.handle_approval_request(event)

            elif event_type == "auto_execution_triggered":
                await self.handle_auto_execution(event)

            elif event_type == "action_validation_failed":
                await self.handle_validation_failed(event)

            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    def _should_notify(self, event: Dict[str, Any]) -> bool:
        """
        Check if event should trigger notification

        Args:
            event: Event to check

        Returns:
            True if should notify
        """
        # Check incident severity
        if "incident" in event:
            incident = event["incident"]
            severity = incident.get("severity", "medium").lower()
            if severity not in config.notify_severity_levels:
                return False

        # Check direct severity field
        if "severity" in event:
            severity = event.get("severity", "medium").lower()
            if severity not in config.notify_severity_levels:
                return False

        return True

    async def handle_incident_detected(self, event: Dict[str, Any]):
        """Handle incident detection event"""
        incident = event.get("incident", event)
        severity = incident.get("severity", "medium").lower()

        logger.info(f"Sending incident notification: {incident.get('incident_id')} (severity: {severity})")

        # Always send to Slack (primary channel)
        await self.slack_client.send_incident_notification(incident)

        # Send email for medium+ severity
        if severity in ['medium', 'high', 'critical'] and self.email_recipients:
            logger.info(f"Sending email notification to {len(self.email_recipients)} recipients")
            await self.email_client.send_incident_alert(
                incident_data=incident,
                to_emails=self.email_recipients,
                severity=severity
            )

        # Send SMS for high+ severity
        if severity in ['high', 'critical'] and self.sms_recipients:
            logger.info(f"Sending SMS notification to {len(self.sms_recipients)} recipients")
            await self.sms_client.send_incident_alert(
                incident_data=incident,
                to_numbers=self.sms_recipients,
                severity=severity
            )

        # Trigger PagerDuty for critical only
        if severity == 'critical':
            logger.info("Triggering PagerDuty incident")
            await self.pagerduty_client.send_incident_alert(
                incident_data=incident,
                severity=severity
            )

    async def handle_analysis_complete(self, event: Dict[str, Any]):
        """Handle analysis completion event"""
        incident = event.get("incident", {})
        analysis = event.get("analysis", {})
        recommendations = event.get("recommendations", [])

        logger.info(f"Sending analysis notification: {incident.get('incident_id')}")

        await self.slack_client.send_analysis_notification(
            incident=incident,
            analysis=analysis,
            recommendations=recommendations
        )

    async def handle_action_executed(self, event: Dict[str, Any]):
        """Handle action execution event"""
        incident_id = event.get("incident_id", "N/A")
        action = event.get("action", {})
        execution_result = event.get("execution_result", {})
        approval_id = event.get("approval_id")

        logger.info(f"Sending action notification: {action.get('type')}")

        await self.slack_client.send_action_notification(
            incident_id=incident_id,
            action_type=action.get("type", "unknown"),
            action_details=action.get("details", {}),
            execution_result=execution_result,
            status=action.get("status", "unknown"),
            approval_id=approval_id
        )

    async def handle_approval_request(self, event: Dict[str, Any]):
        """Handle approval request event"""
        incident_id = event.get("incident_id", "N/A")
        approval_id = event.get("approval_id", "N/A")
        action = event.get("action", {})
        validation = event.get("validation", {})

        # Extract details from action
        action_type = action.get("type", "unknown")
        action_details = action.get("details", {})

        # Get severity and confidence from validation or action
        severity = validation.get("severity", "medium")
        confidence = validation.get("confidence", 0)
        reasoning = validation.get("approval_reasons", ["Action requires approval"])[0]

        logger.info(f"Sending approval request notification: {approval_id}")

        await self.slack_client.send_approval_request_notification(
            incident_id=incident_id,
            approval_id=approval_id,
            action_type=action_type,
            action_details=action_details,
            severity=severity,
            confidence=confidence,
            reasoning=reasoning
        )

    async def handle_auto_execution(self, event: Dict[str, Any]):
        """Handle auto-execution triggered event"""
        incident_id = event.get("incident_id", "N/A")
        action = event.get("action", {})

        logger.info(f"Auto-execution triggered for incident {incident_id}")

        # Send a simple notification that auto-execution is happening
        text = f"🤖 Auto-executing action: {action.get('type')} on {action.get('details', {}).get('target', 'unknown')}"
        await self.slack_client.send_message(text=text)

    async def handle_validation_failed(self, event: Dict[str, Any]):
        """Handle validation failed event"""
        incident_id = event.get("incident_id", "N/A")
        action = event.get("action", {})
        validation = event.get("validation", {})

        logger.warning(f"Validation failed for incident {incident_id}")

        # Send notification about validation failure
        reasons = validation.get("failure_reasons", ["Unknown reason"])
        text = f"⚠️ Action validation failed for incident {incident_id}: {', '.join(reasons)}"
        await self.slack_client.send_message(text=text)

    def setup_signal_handlers(self):
        """Setup graceful shutdown on SIGINT/SIGTERM"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    agent = NotifierAgent()
    agent.setup_signal_handlers()

    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
