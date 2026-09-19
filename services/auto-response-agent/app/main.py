"""
Auto-Response Agent - Main Orchestrator

Autonomous remediation agent that:
1. Consumes analysis events with recommendations
2. Validates recommendations with safety checks
3. Decides: auto-execute or request approval
4. Executes actions via K8s
5. Publishes results
"""
import logging
import asyncio
import signal
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import config
from app.executors import ExecutorFactory
from app.approval_client import ApprovalClient
from app.action_validator import ActionValidator
from app.event_consumer import EventConsumer
from app.approval_consumer import ApprovalConsumer
from app.event_publisher import EventPublisher

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoResponseAgent:
    """Main auto-response agent orchestrator"""

    def __init__(self):
        """Initialize agent with all components"""
        logger.info(f"Initializing Auto-Response Agent v{config.agent_version}")

        # Initialize executor (auto-detects Docker Compose or Kubernetes)
        self.executor = ExecutorFactory.create_executor(
            dry_run=config.k8s_dry_run,
            # K8s-specific config
            in_cluster=config.k8s_in_cluster,
            namespace=config.k8s_namespace,
            # Docker Compose config
            compose_file=config.docker_compose_file if hasattr(config, 'docker_compose_file') else '/compose/docker-compose.yml',
            project_name=config.docker_compose_project if hasattr(config, 'docker_compose_project') else None
        )
        logger.info(f"Initialized executor: {self.executor.get_executor_type()}")

        self.approval_client = ApprovalClient(
            api_url=config.approval_api_url,
            timeout=config.approval_timeout,
            poll_interval=config.approval_poll_interval
        )

        self.action_validator = ActionValidator(
            auto_execute_threshold=config.auto_execute_threshold,
            require_approval_actions=config.require_approval_actions,
            require_approval_criticality=config.require_approval_criticality,
            max_scale_replicas=config.max_scale_replicas,
            min_scale_replicas=config.min_scale_replicas
        )

        self.event_consumer = EventConsumer(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange,
            routing_key=config.rabbitmq_analysis_routing_key,
            queue_name="auto_response_queue"
        )

        self.approval_consumer = ApprovalConsumer(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange,
            queue_name="auto_response_approval_queue"
        )

        self.event_publisher = EventPublisher(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange
        )

        # Track pending actions waiting for approval
        # Format: {approval_id: {incident_id, action, action_details, timestamp}}
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the agent"""
        logger.info("=" * 60)
        logger.info(f"Starting Auto-Response Agent v{config.agent_version}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Dry-run mode: {config.k8s_dry_run}")
        logger.info(f"Auto-execute threshold: {config.auto_execute_threshold}%")
        logger.info("=" * 60)

        try:
            # Connect to services
            await self._connect_services()

            # Setup message handlers
            self.event_consumer.set_message_handler(self.on_analysis_complete)
            self.approval_consumer.set_message_handler(self.on_approval_decision)

            # Start consuming events
            self.running = True
            logger.info("✓ Auto-Response Agent is ready and listening for events")

            # Start consuming in background (both analysis and approval events)
            consume_task = asyncio.create_task(self.event_consumer.start_consuming())
            approval_task = asyncio.create_task(self.approval_consumer.start_consuming())

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Cancel consuming tasks
            consume_task.cancel()
            approval_task.cancel()
            try:
                await consume_task
                await approval_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"Failed to start agent: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the agent gracefully"""
        logger.info("Stopping Auto-Response Agent...")
        self.running = False

        try:
            await self.event_consumer.disconnect()
            await self.approval_consumer.disconnect()
            await self.event_publisher.disconnect()
            await self.approval_client.disconnect()
            logger.info("✓ Auto-Response Agent stopped gracefully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def _connect_services(self):
        """Connect to all external services"""
        logger.info("Connecting to services...")

        # Connect RabbitMQ consumer for analysis events
        await self.event_consumer.connect()

        # Connect RabbitMQ consumer for approval decisions
        await self.approval_consumer.connect()

        # Connect RabbitMQ publisher
        await self.event_publisher.connect()

        # Connect approval client
        await self.approval_client.connect()

        # Check executor availability
        executor_healthy = await self.executor.health_check()
        if not executor_healthy:
            logger.warning(f"{self.executor.get_executor_type()} executor not available - actions may fail")
        else:
            logger.info(f"✓ {self.executor.get_executor_type()} executor available and healthy")

        logger.info("✓ All services connected")

    async def on_analysis_complete(self, event: Dict[str, Any]):
        """
        Handle analysis complete event

        Args:
            event: Analysis complete event with recommendations
        """
        incident_id = event.get("incident_id") or event.get("original_incident", {}).get("incident_id")
        recommendations = event.get("recommendations", [])

        logger.info(
            f"Processing analysis for incident {incident_id}: "
            f"{len(recommendations)} recommendations"
        )

        if not recommendations:
            logger.info(f"No recommendations for incident {incident_id}, creating approval for manual review")
            # Send to approval dashboard for manual review even without recommendations
            await self.create_manual_review_approval(
                incident_id=incident_id,
                incident=event.get("original_incident", {}),
                analysis=event.get("analysis", {})
            )
            return

        # Process each recommendation
        for idx, recommendation in enumerate(recommendations, 1):
            logger.info(f"Processing recommendation {idx}/{len(recommendations)}")

            try:
                await self.process_recommendation(
                    recommendation=recommendation,
                    incident=event.get("incident", {}),
                    analysis=event.get("analysis", {})
                )
            except Exception as e:
                logger.error(f"Error processing recommendation: {e}", exc_info=True)

    async def process_recommendation(
        self,
        recommendation: Dict[str, Any],
        incident: Dict[str, Any],
        analysis: Dict[str, Any]
    ):
        """
        Process a single recommendation

        Flow:
        1. Validate recommendation
        2. Decide: auto-execute or request approval
        3. Execute action
        4. Publish result

        Args:
            recommendation: Recommended action
            incident: Source incident
            analysis: Analysis results
        """
        action_type = recommendation.get("action_type")
        target = recommendation.get("target")
        incident_id = incident.get("incident_id")

        logger.info(f"Processing recommendation: {action_type} on {target}")

        # Step 1: Validate recommendation
        validation = await self.action_validator.validate_recommendation(
            recommendation=recommendation,
            incident=incident,
            analysis=analysis
        )

        if not validation["valid"]:
            logger.warning(
                f"Recommendation validation failed: {validation.get('failure_reasons', [])}"
            )
            await self.event_publisher.publish_action_validation_failed(
                incident_id=incident_id,
                action_type=action_type,
                action_details=recommendation,
                validation_result=validation
            )
            return

        # Step 2: Decide execution path
        if validation["auto_execute"]:
            logger.info(f"Auto-executing action: {action_type} (confidence: {recommendation.get('confidence')}%)")
            await self.event_publisher.publish_auto_execution_triggered(
                incident_id=incident_id,
                action_type=action_type,
                action_details=recommendation,
                validation_result=validation
            )
            await self.execute_action(
                recommendation=recommendation,
                incident_id=incident_id,
                approved=True,
                approval_id=None
            )

        elif validation["requires_approval"]:
            logger.info(f"Requesting approval for action: {action_type}")
            await self.request_and_wait_approval(
                recommendation=recommendation,
                incident=incident,
                validation=validation
            )

        else:
            logger.warning(f"Action cannot be executed and does not require approval (unexpected state)")

    async def request_and_wait_approval(
        self,
        recommendation: Dict[str, Any],
        incident: Dict[str, Any],
        validation: Dict[str, Any]
    ):
        """
        Request human approval and store action for later execution

        Args:
            recommendation: Recommended action
            incident: Source incident
            validation: Validation results
        """
        incident_id = incident.get("incident_id")
        action_type = recommendation.get("action_type")

        # Create approval request
        approval_request = await self.approval_client.create_approval_request(
            incident_id=incident_id,
            action_type=action_type,
            action_details=recommendation,
            severity=incident.get("severity", "medium"),
            confidence=recommendation.get("confidence", 0),
            reasoning=recommendation.get("reasoning", "No reasoning provided")
        )

        # approval_request is now just the ID (int)
        approval_id = approval_request

        logger.info(f"✓ Created approval request: {approval_id} for action: {action_type}")

        # Store pending action for execution when approved
        self.pending_approvals[str(approval_id)] = {
            "incident_id": incident_id,
            "recommendation": recommendation,
            "incident": incident,
            "validation": validation,
            "timestamp": datetime.utcnow().isoformat(),
            "action_type": action_type
        }

        logger.info(f"✓ Action stored, waiting for human approval decision via RabbitMQ...")

        # Publish pending approval event
        await self.event_publisher.publish_action_pending_approval(
            incident_id=incident_id,
            action_type=action_type,
            action_details=recommendation,
            approval_id=approval_id,
            validation_result=validation
        )

    async def create_manual_review_approval(
        self,
        incident_id: str,
        incident: Dict[str, Any],
        analysis: Dict[str, Any]
    ):
        """
        Create approval request for incidents without recommendations (manual review)
        
        Args:
            incident_id: Incident ID
            incident: Source incident
            analysis: Analysis results
        """
        severity = incident.get("severity", "medium")
        metric = incident.get("metric", "unknown")
        
        logger.info(f"Creating manual review approval for incident {incident_id}")
        
        # Create approval request for manual review
        approval_request = await self.approval_client.create_approval_request(
            incident_id=incident_id,
            action_type="manual_review",
            action_details={
                "metric": metric,
                "severity": severity,
                "analysis": analysis.get("summary", "No analysis summary"),
                "requires_manual_intervention": True
            },
            severity=severity,
            confidence=analysis.get("confidence", 0),
            reasoning=f"Incident requires manual review: {analysis.get('summary', 'No automated recommendation available')}"
        )
        
        # approval_request is now just the ID (int)
        approval_id = approval_request
        logger.info(f"✓ Created manual review approval: {approval_id}")
        
        # Publish event for notification
        await self.event_publisher.publish_action_pending_approval(
            incident_id=incident_id,
            action_type="manual_review",
            action_details={"type": "manual_review", "metric": metric},
            approval_id=approval_id,
            validation_result={"manual_review": True}
        )

    async def on_approval_decision(self, decision_event: Dict[str, Any]):
        """
        Handle approval decision from approval dashboard

        Args:
            decision_event: Approval decision event from RabbitMQ
                           Contains: approval_id, decision ('approved' or 'rejected'), data
        """
        approval_id = str(decision_event.get("approval_id"))
        decision = decision_event.get("decision")  # 'approved' or 'rejected'
        approval_data = decision_event.get("data", {})

        logger.info(f"📨 Received approval decision: ID={approval_id}, Decision={decision}")

        # Check if we have this pending action
        if approval_id not in self.pending_approvals:
            logger.warning(f"⚠️ Approval {approval_id} not found in pending actions - may have been processed already")
            return

        # Get the pending action
        pending_action = self.pending_approvals[approval_id]
        incident_id = pending_action["incident_id"]
        recommendation = pending_action["recommendation"]
        action_type = pending_action["action_type"]

        if decision == "approved":
            logger.info(f"✅ Approval {approval_id} APPROVED - executing action: {action_type}")
            
            # Execute the approved action
            try:
                await self.execute_action(
                    recommendation=recommendation,
                    incident_id=incident_id,
                    approved=True,
                    approval_id=approval_id
                )
                logger.info(f"✓ Action executed successfully after approval: {approval_id}")
            except Exception as e:
                logger.error(f"❌ Failed to execute approved action {approval_id}: {e}", exc_info=True)
                
        elif decision == "rejected":
            logger.info(f"❌ Approval {approval_id} REJECTED - action will not be executed")
            
            # Publish rejection event
            await self.event_publisher.publish_action_executed(
                incident_id=incident_id,
                action_type=action_type,
                action_details=recommendation,
                execution_result={"status": "rejected", "message": "Action rejected by human approver"},
                status="rejected",
                approval_id=approval_id
            )
        
        # Remove from pending approvals
        del self.pending_approvals[approval_id]
        logger.info(f"✓ Removed approval {approval_id} from pending queue")

    async def execute_action(
        self,
        recommendation: Dict[str, Any],
        incident_id: str,
        approved: bool,
        approval_id: Optional[str]
    ):
        """
        Execute a validated and approved action

        Args:
            recommendation: Recommended action
            incident_id: Source incident ID
            approved: Whether action was approved
            approval_id: Approval ID if applicable
        """
        action_type = recommendation.get("action_type")
        target = recommendation.get("target")
        parameters = recommendation.get("parameters", {})
        namespace = recommendation.get("namespace")

        logger.info(f"Executing action: {action_type} on {target}")

        try:
            # Route to appropriate executor method
            if action_type == "scale_deployment":
                result = await self.executor.scale(
                    target=target,
                    replicas=parameters.get("replicas", 2),
                    namespace=namespace,
                    min_replicas=config.min_scale_replicas,
                    max_replicas=config.max_scale_replicas
                )

            elif action_type == "restart_pods":
                result = await self.executor.restart(
                    target=target,
                    namespace=namespace,
                    grace_period=parameters.get("grace_period", 30)
                )

            elif action_type == "rollback_deployment":
                result = await self.executor.rollback(
                    target=target,
                    namespace=namespace,
                    revision=parameters.get("revision")
                )

            else:
                logger.error(f"Unknown action type: {action_type}")
                result = {
                    "action": action_type,
                    "status": "failed",
                    "error": f"Unknown action type: {action_type}"
                }

            # Record action for cooldown tracking
            self.action_validator.record_action(target, action_type)

            # Convert ExecutionResult to dict if needed
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result

            # Publish execution result
            await self.event_publisher.publish_action_executed(
                incident_id=incident_id,
                action_type=action_type,
                action_details=recommendation,
                execution_result=result_dict,
                status=result_dict.get("status", "unknown"),
                approval_id=approval_id
            )

            # Update approval with progress if applicable
            if approval_id:
                await self.approval_client.update_approval_progress(
                    approval_id=approval_id,
                    progress=f"Action executed: {result_dict.get('status')}",
                    metadata=result_dict
                )

            logger.info(f"Action execution completed: {result_dict.get('status')}")

        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)

            # Publish failure event
            await self.event_publisher.publish_action_executed(
                incident_id=incident_id,
                action_type=action_type,
                action_details=recommendation,
                execution_result={"error": str(e)},
                status="failed",
                approval_id=approval_id,
                error=str(e)
            )

    def setup_signal_handlers(self):
        """Setup graceful shutdown on SIGINT/SIGTERM"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    agent = AutoResponseAgent()
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
