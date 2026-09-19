"""
Memory Agent - Main Orchestrator

Autonomous memory agent that:
1. Consumes all agent events from RabbitMQ
2. Stores incidents, analyses, and resolutions
3. Generates and stores embeddings for semantic search
4. Detects recurring patterns
5. Provides learning insights to other agents
"""
import logging
import asyncio
import signal
from typing import Dict, Any
from datetime import datetime
import aio_pika

from app.config import config
from app.incident_store import IncidentStore
from app.vector_store import VectorStore
from app.pattern_detector import PatternDetector

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MemoryAgent:
    """Main memory agent orchestrator"""

    def __init__(self):
        """Initialize agent with all components"""
        logger.info(f"Initializing Memory Agent v{config.agent_version}")

        # Initialize incident store (PostgreSQL)
        self.incident_store = IncidentStore(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password,
            min_pool_size=config.db_pool_min,
            max_pool_size=config.db_pool_max,
            timeout=config.db_connection_timeout // 1000
        )

        # Initialize vector store (Qdrant Cloud)
        self.vector_store = VectorStore(
            qdrant_host=config.qdrant_host,
            qdrant_port=config.qdrant_http_port,
            qdrant_api_key=config.qdrant_api_key,
            collection_name=config.qdrant_collection_name,
            vector_size=config.qdrant_vector_size,
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model
        )

        # Initialize pattern detector
        self.pattern_detector = PatternDetector(
            incident_store=self.incident_store,
            vector_store=self.vector_store,
            similarity_threshold=config.pattern_similarity_threshold,
            min_occurrences=config.pattern_min_occurrences,
            time_window_hours=config.pattern_time_window_hours
        )

        # RabbitMQ connection
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.rabbitmq_queue = None

        self.running = False
        self.shutdown_event = asyncio.Event()

        # Event tracking
        self.pending_incidents = {}  # incident_id -> incident data

    async def start(self):
        """Start the agent"""
        logger.info("=" * 60)
        logger.info(f"Starting Memory Agent v{config.agent_version}")
        logger.info(f"Environment: {config.environment}")
        logger.info("=" * 60)

        try:
            # Connect to services
            await self._connect_services()

            # Start background tasks
            self.running = True
            pattern_detection_task = asyncio.create_task(self._pattern_detection_loop())
            cleanup_task = asyncio.create_task(self._cleanup_loop())

            # Start consuming events
            logger.info("✓ Memory Agent is ready and listening for events")

            # Start consuming in background
            consume_task = asyncio.create_task(self._start_consuming())

            # Wait for shutdown signal
            await self.shutdown_event.wait()

            # Cancel all tasks
            for task in [consume_task, pattern_detection_task, cleanup_task]:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Failed to start agent: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the agent gracefully"""
        logger.info("Stopping Memory Agent...")
        self.running = False

        try:
            # Close RabbitMQ connection
            if self.rabbitmq_channel:
                await self.rabbitmq_channel.close()
            if self.rabbitmq_connection:
                await self.rabbitmq_connection.close()

            # Close database connections
            await self.incident_store.disconnect()

            logger.info("✓ Memory Agent stopped gracefully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def _connect_services(self):
        """Connect to all external services"""
        logger.info("Connecting to services...")

        # Connect to PostgreSQL
        postgres_ok = await self.incident_store.connect()
        if not postgres_ok:
            raise Exception("Failed to connect to PostgreSQL")

        # Connect to Qdrant Cloud
        qdrant_ok = await self.vector_store.connect()
        if not qdrant_ok:
            raise Exception("Failed to connect to Qdrant")

        # Connect to RabbitMQ
        rabbitmq_ok = await self._connect_rabbitmq()
        if not rabbitmq_ok:
            raise Exception("Failed to connect to RabbitMQ")

        logger.info("✓ All services connected")

    async def _connect_rabbitmq(self) -> bool:
        """Connect to RabbitMQ and setup queue"""
        try:
            logger.info(f"Connecting to RabbitMQ at {config.rabbitmq_host}:{config.rabbitmq_port}")

            # Create connection
            self.rabbitmq_connection = await aio_pika.connect_robust(
                host=config.rabbitmq_host,
                port=config.rabbitmq_port,
                login=config.rabbitmq_user,
                password=config.rabbitmq_password,
                virtualhost=config.rabbitmq_vhost
            )

            # Create channel
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            await self.rabbitmq_channel.set_qos(prefetch_count=config.rabbitmq_prefetch_count)

            # Declare exchange
            exchange = await self.rabbitmq_channel.declare_exchange(
                config.rabbitmq_exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            # Declare queue
            self.rabbitmq_queue = await self.rabbitmq_channel.declare_queue(
                "memory_queue",
                durable=config.rabbitmq_queue_durable,
                auto_delete=config.rabbitmq_queue_auto_delete
            )

            # Bind to all routing keys
            routing_keys = [
                config.rabbitmq_incident_routing_key,
                config.rabbitmq_analysis_routing_key,
                config.rabbitmq_action_routing_key,
                config.rabbitmq_approval_routing_key
            ]

            for routing_key in routing_keys:
                await self.rabbitmq_queue.bind(exchange, routing_key=routing_key)
                logger.info(f"Bound queue to routing key: {routing_key}")

            logger.info("✓ RabbitMQ connected and configured")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}", exc_info=True)
            return False

    async def _start_consuming(self):
        """Start consuming messages from RabbitMQ"""
        try:
            async with self.rabbitmq_queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            event = message.body.decode()
                            import json
                            event_data = json.loads(event)

                            await self.on_agent_event(event_data)

                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)

    async def on_agent_event(self, event: Dict[str, Any]):
        """
        Handle agent event

        Args:
            event: Agent event with type and payload
        """
        event_type = event.get("event_type", "unknown")
        logger.info(f"Processing event: {event_type}")

        try:
            # Route to appropriate handler
            if event_type == "incident_detected":
                await self.handle_incident_detected(event)

            elif event_type == "analysis_complete":
                await self.handle_analysis_complete(event)

            elif event_type == "action_executed":
                await self.handle_action_executed(event)

            elif event_type == "action_pending_approval":
                # Just track for now, actual execution handled by auto-response
                logger.info(f"Action pending approval: {event.get('approval_id')}")

            else:
                logger.debug(f"Ignoring event type: {event_type}")

        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    async def handle_incident_detected(self, event: Dict[str, Any]):
        """
        Handle incident detection event

        Args:
            event: Incident event
        """
        incident = event.get("incident", event)
        incident_id = incident.get("incident_id")

        logger.info(f"Storing incident: {incident_id}")

        # Store incident in PostgreSQL
        await self.incident_store.store_incident(incident)

        # Keep in memory for later embedding (after analysis)
        self.pending_incidents[incident_id] = {
            "incident": incident,
            "analysis": None,
            "resolution": None
        }

    async def handle_analysis_complete(self, event: Dict[str, Any]):
        """
        Handle analysis completion event

        Args:
            event: Analysis event
        """
        incident = event.get("incident", {})
        incident_id = incident.get("incident_id")
        analysis = event.get("analysis", {})

        logger.info(f"Storing analysis for incident: {incident_id}")

        # Store analysis in PostgreSQL
        await self.incident_store.store_analysis(incident_id, analysis)

        # Update pending incident with analysis
        if incident_id in self.pending_incidents:
            self.pending_incidents[incident_id]["analysis"] = analysis
        else:
            self.pending_incidents[incident_id] = {
                "incident": incident,
                "analysis": analysis,
                "resolution": None
            }

    async def handle_action_executed(self, event: Dict[str, Any]):
        """
        Handle action execution event

        Args:
            event: Action execution event
        """
        incident_id = event.get("incident_id")
        action = event.get("action", {})
        execution_result = event.get("execution_result", {})

        # Determine success
        status = execution_result.get("status", "unknown")
        success = status == "success"

        logger.info(f"Storing resolution for incident: {incident_id} (success={success})")

        # Store resolution in PostgreSQL
        await self.incident_store.store_resolution(
            incident_id=incident_id,
            action=action,
            execution_result=execution_result,
            success=success
        )

        # Update pending incident and create embedding
        if incident_id in self.pending_incidents:
            self.pending_incidents[incident_id]["resolution"] = {
                "action_type": action.get("type"),
                "action_details": action.get("details"),
                "success": success,
                "execution_result": execution_result
            }

            # Generate and store embedding (complete picture now)
            await self._create_embedding_for_incident(incident_id)

            # Remove from pending
            del self.pending_incidents[incident_id]

    async def _create_embedding_for_incident(self, incident_id: str):
        """
        Create and store embedding for complete incident

        Args:
            incident_id: Incident ID
        """
        try:
            pending = self.pending_incidents.get(incident_id)
            if not pending:
                logger.warning(f"No pending data for incident: {incident_id}")
                return

            incident = pending.get("incident")
            analysis = pending.get("analysis")
            resolution = pending.get("resolution")

            if not incident:
                logger.warning(f"No incident data for: {incident_id}")
                return

            logger.info(f"Creating embedding for incident: {incident_id}")

            # Generate and store embedding
            success = await self.vector_store.store_incident_embedding(
                incident=incident,
                analysis=analysis,
                resolution=resolution
            )

            if success:
                logger.info(f"✓ Embedding stored for incident: {incident_id}")
            else:
                logger.error(f"Failed to store embedding for incident: {incident_id}")

        except Exception as e:
            logger.error(f"Error creating embedding: {e}", exc_info=True)

    async def _pattern_detection_loop(self):
        """Background task for periodic pattern detection"""
        logger.info("Starting pattern detection loop")

        while self.running:
            try:
                # Wait before first run
                await asyncio.sleep(300)  # 5 minutes

                if not self.running:
                    break

                logger.info("Running pattern detection...")
                patterns = await self.pattern_detector.detect_patterns()

                if patterns:
                    logger.info(f"Detected {len(patterns)} patterns")

                    # Log pattern details
                    for pattern in patterns:
                        logger.info(
                            f"  - {pattern.get('pattern_type')}: "
                            f"{pattern.get('description')} "
                            f"({pattern.get('occurrence_count')} occurrences)"
                        )

                        # Get recommendations
                        recommendations = await self.pattern_detector.get_pattern_recommendations(pattern)
                        for rec in recommendations:
                            logger.info(f"    {rec}")

            except Exception as e:
                logger.error(f"Error in pattern detection loop: {e}", exc_info=True)

            # Run every hour
            await asyncio.sleep(3600)

    async def _cleanup_loop(self):
        """Background task for periodic data cleanup"""
        logger.info("Starting cleanup loop")

        while self.running:
            try:
                # Wait before first run
                await asyncio.sleep(3600)  # 1 hour

                if not self.running:
                    break

                logger.info("Running data cleanup...")
                await self.incident_store.cleanup_old_data()

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

            # Run every 24 hours
            await asyncio.sleep(86400)

    def setup_signal_handlers(self):
        """Setup graceful shutdown on SIGINT/SIGTERM"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def health_check():
    """Health check for Docker healthcheck"""
    # Simple health check - just return success
    return True


async def main():
    """Main entry point"""
    agent = MemoryAgent()
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
