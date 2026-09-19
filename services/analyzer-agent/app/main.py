"""
Analyzer Agent - Main Entry Point

This agent listens for incident events, performs LLM-powered root cause analysis,
and publishes recommendations for remediation.
"""
import asyncio
import logging
import signal
import sys
import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import redis.asyncio as redis

from app.config import config
from app.llm_analyzer import LLMAnalyzer
from app.log_fetcher import LogFetcher
from app.rag_search import RAGSearch
from app.event_consumer import EventConsumer
from app.event_publisher import EventPublisher
from app.prompts import build_analysis_prompt
from app.action_mapper import ActionMapper

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """Analyzer Agent - Performs LLM-powered root cause analysis"""

    def __init__(self):
        self.running = False
        self.llm_analyzer = LLMAnalyzer(
            service_url=config.llm_service_url,
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=config.llm_temperature
        )
        self.log_fetcher = LogFetcher() if config.fetch_logs_enabled else None
        self.rag_search = RAGSearch(
            host=config.qdrant_host,
            port=config.qdrant_port,
            collection=config.qdrant_collection
        ) if config.rag_enabled else None

        self.event_consumer = EventConsumer(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost
        )
        self.event_publisher = EventPublisher(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange
        )
        
        # Redis cache for LLM responses (prevent redundant API calls)
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = 300  # 5 minutes cache for identical incidents
        
        # Incident processing queue (serialize LLM calls)
        self.incident_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.queue_processor_task: Optional[asyncio.Task] = None

        logger.info(f"✓ Analyzer Agent initialized (version {config.agent_version})")

    async def start(self):
        """Start the analyzer agent"""
        self.running = True
        logger.info("🚀 Starting Analyzer Agent...")

        # Connect to dependencies
        await self.event_publisher.connect()
        await self.event_consumer.connect()
        
        # Connect to Redis for LLM response caching
        try:
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password,
                db=config.redis_db,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"✓ Redis cache connected (TTL: {self.cache_ttl}s)")
        except Exception as e:
            logger.warning(f"⚠️  Redis cache unavailable: {e}")
            self.redis_client = None

        # Subscribe to incident events
        await self.event_consumer.subscribe(
            exchange=config.rabbitmq_exchange,
            routing_key="monitoring.incident.*",
            callback=self.on_incident_detected
        )
        
        # Start queue processor (serialize LLM calls)
        self.queue_processor_task = asyncio.create_task(self._process_incident_queue())
        logger.info("✅ Incident queue processor started (one-at-a-time processing)")

        logger.info(f"📊 Listening for incidents on routing key: monitoring.incident.*")
        logger.info(f"🤖 LLM Provider: {config.llm_provider} ({config.llm_model})")
        logger.info(f"🔍 RAG enabled: {config.rag_enabled}")

        # Keep running
        while self.running:
            await asyncio.sleep(1)

    async def on_incident_detected(self, event: Dict[str, Any]):
        """
        Handle incident detection event by adding to processing queue

        Args:
            event: Incident event from monitoring agent
        """
        incident_id = event.get("incident_id", str(uuid.uuid4()))
        metric = event.get("data", {}).get("metric", "unknown")
        severity = event.get("severity", "medium")

        logger.info(f"🔍 Queuing incident {incident_id}: {metric} (severity: {severity})")
        
        try:
            # Add to queue (non-blocking with timeout)
            await asyncio.wait_for(
                self.incident_queue.put(event),
                timeout=5.0
            )
            logger.debug(f"Queue size: {self.incident_queue.qsize()}")
        except asyncio.TimeoutError:
            logger.error(f"⚠️  Queue full! Dropping incident {incident_id}")
    
    async def _process_incident_queue(self):
        """
        Process incidents from queue one at a time to prevent parallel LLM calls
        """
        logger.info("🔄 Starting incident queue processor...")
        
        while self.running:
            try:
                # Get next incident from queue
                event = await self.incident_queue.get()
                
                # Process it (LLM call happens here)
                await self._analyze_incident(event)
                
                # Mark task as done
                self.incident_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _analyze_incident(self, event: Dict[str, Any]):
        """
        Analyze a single incident (called by queue processor)
        
        Args:
            event: Incident event from monitoring agent
        """        
        incident_id = event.get("incident_id", str(uuid.uuid4()))
        metric = event.get("data", {}).get("metric", "unknown")
        severity = event.get("severity", "medium")

        logger.info(f"🔍 Analyzing incident {incident_id}: {metric} (severity: {severity})")

        try:
            # Step 1: Fetch relevant logs (if enabled)
            logs = []
            if self.log_fetcher:
                logs = await self.fetch_logs_for_incident(event)
                logger.debug(f"Fetched {len(logs)} log lines")

            # Step 2: Search for similar past incidents (if RAG enabled)
            similar_incidents = []
            if self.rag_search:
                similar_incidents = await self.search_similar_incidents(event)
                logger.debug(f"Found {len(similar_incidents)} similar incidents")

            # Step 3: Perform LLM-powered root cause analysis
            analysis = await self.analyze_with_llm(event, logs, similar_incidents)
            logger.info(f"✓ Analysis complete: confidence={analysis['confidence']}%")

            # Step 4: Generate fix recommendations
            recommendations = self.generate_recommendations(analysis, event)
            logger.info(f"✓ Generated {len(recommendations)} recommendations")

            # Step 5: Publish analysis result
            await self.publish_analysis(incident_id, event, analysis, recommendations)
            logger.info(f"✓ Published analysis for incident {incident_id}")

        except Exception as e:
            logger.error(f"Error analyzing incident {incident_id}: {e}", exc_info=True)
            # Publish error event
            await self.publish_analysis_error(incident_id, event, str(e))

    async def fetch_logs_for_incident(self, event: Dict[str, Any]) -> List[str]:
        """
        Fetch relevant logs for the incident

        Args:
            event: Incident event

        Returns:
            List of log lines
        """
        affected_services = event.get("data", {}).get("affected_services", [])
        if not affected_services:
            return []

        try:
            logs = await self.log_fetcher.fetch_logs(
                services=affected_services,
                time_window=config.log_fetch_window,
                max_lines=config.max_log_lines
            )
            return logs
        except Exception as e:
            logger.warning(f"Failed to fetch logs: {e}")
            return []

    async def search_similar_incidents(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for similar past incidents using RAG

        Args:
            event: Current incident event

        Returns:
            List of similar incidents with metadata
        """
        # Skip if RAG is disabled
        if not config.rag_enabled or not self.rag_search:
            logger.info("RAG disabled or not available, skipping similar incident search")
            return []
        
        metric = event.get("data", {}).get("metric", "")
        affected_services = event.get("data", {}).get("affected_services", [])

        # Build search query
        query = f"Incident: {metric}"
        if affected_services:
            query += f" affecting {', '.join(affected_services)}"

        try:
            similar = await self.rag_search.search(
                query=query,
                top_k=config.rag_top_k,
                score_threshold=config.rag_similarity_threshold
            )
            return similar
        except Exception as e:
            logger.warning(f"Failed to search similar incidents: {e}")
            return []

    async def analyze_with_llm(
        self,
        event: Dict[str, Any],
        logs: List[str],
        similar_incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform LLM-powered root cause analysis with caching

        Args:
            event: Incident event
            logs: Fetched log lines
            similar_incidents: Similar past incidents

        Returns:
            Analysis result with root cause, confidence, and recommended actions
        """
        # Check if mock mode is enabled
        if config.llm_mock_mode:
            logger.warning("⚠️  LLM Mock Mode enabled - using mock analysis")
            return self._generate_mock_analysis(event)
        
        # Generate cache key from incident characteristics
        cache_key = self._generate_cache_key(event)
        
        # Check cache first
        cached_analysis = await self._get_cached_analysis(cache_key)
        if cached_analysis:
            logger.info(f"📦 Using cached LLM analysis (key: {cache_key[:16]}...)")
            return cached_analysis
        
        # Build comprehensive prompt for LLM
        prompt = self._build_analysis_prompt(event, logs, similar_incidents)

        try:
            # Call LLM for analysis
            analysis = await self.llm_analyzer.analyze(
                prompt=prompt,
                timeout=config.analysis_timeout
            )
            
            # Cache the result for future identical incidents
            await self._cache_analysis(cache_key, analysis)
            
            return analysis
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}. Falling back to mock analysis.")
            return self._generate_mock_analysis(event)
    
    def _generate_cache_key(self, event: Dict[str, Any]) -> str:
        """
        Generate cache key from incident characteristics
        Same metric + similar value + same service = same cache key
        """
        data = event.get("data", {})
        metric = data.get("metric", "unknown")
        current_value = data.get("current_value", 0)
        affected_services = data.get("affected_services", [])
        severity = event.get("severity", "unknown")
        
        # Round value to reduce cache misses (e.g., 94.5% and 95.2% = same issue)
        value_bucket = int(current_value / 10) * 10  # Bucket into 10% ranges
        
        # Create unique but consistent key
        key_parts = [
            metric,
            str(value_bucket),
            "-".join(sorted(affected_services)),
            severity
        ]
        key_string = ":".join(key_parts)
        
        # Hash to create clean cache key
        return f"llm_analysis:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached LLM analysis if available"""
        if not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        return None
    
    async def _cache_analysis(self, cache_key: str, analysis: Dict[str, Any]) -> None:
        """Store LLM analysis in cache"""
        if not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(analysis)
            )
            logger.debug(f"💾 Cached LLM analysis (TTL: {self.cache_ttl}s)")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def _generate_mock_analysis(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock analysis when LLM is unavailable"""
        data = event.get("data", {})
        metric = data.get("metric", "unknown")
        severity = event.get("severity", "medium")
        current_value = data.get("current_value", 0)
        
        # Generate appropriate recommendation based on metric
        if "cpu" in metric.lower():
            action = "scale_deployment"
            root_cause = f"High CPU usage detected ({current_value}%)"
            explanation = "CPU utilization has exceeded normal thresholds, indicating increased load"
            immediate_action = f"Scale up deployment to handle increased CPU load"
            confidence = 75.0
        elif "memory" in metric.lower():
            action = "restart_pods"
            root_cause = f"High memory usage detected ({current_value} MB)"
            explanation = "Memory consumption has exceeded thresholds, possible memory leak"
            immediate_action = "Restart pods to clear memory and monitor for leaks"
            confidence = 70.0
        else:
            action = "investigate"
            root_cause = f"Anomaly detected in {metric}"
            explanation = f"Metric {metric} has deviated from normal patterns"
            immediate_action = "Investigate the root cause of the anomaly"
            confidence = 65.0
        
        return {
            "root_cause": root_cause,
            "explanation": explanation,
            "confidence": confidence,
            "immediate_actions": [immediate_action],
            "recommendations": [{
                "action_type": action,
                "target": data.get("affected_services", ["test_app"])[0] if data.get("affected_services") else "test_app",
                "parameters": {"replicas": 3} if action == "scale_deployment" else {},
                "reason": immediate_action,
                "criticality": "high" if severity == "high" else "medium",
                "estimated_impact": "Should resolve issue within 2-3 minutes",
                "approval_required": True,
                "confidence": confidence
            }]
        }

    def _build_analysis_prompt(
        self,
        event: Dict[str, Any],
        logs: List[str],
        similar_incidents: List[Dict[str, Any]]
    ) -> str:
        """Build comprehensive prompt for LLM analysis using new structured format"""
        data = event.get("data", {})

        # Extract incident details
        service_name = data.get('affected_services', ['unknown'])[0] if data.get('affected_services') else 'unknown'
        metric_name = data.get('metric', 'unknown')
        current_value = str(data.get('current_value', 'N/A'))
        threshold = str(data.get('threshold', 'N/A'))
        severity = event.get('severity', 'medium')
        affected_services = data.get('affected_services', [])
        cluster = data.get('cluster', 'unknown')
        namespace = data.get('namespace', 'unknown')
        timestamp = event.get('timestamp', 'unknown')

        # Use new structured prompt builder
        prompt = build_analysis_prompt(
            service_name=service_name,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            severity=severity,
            affected_services=affected_services,
            cluster=cluster,
            namespace=namespace,
            timestamp=timestamp,
            logs=logs,
            similar_incidents=similar_incidents
        )

        return prompt

    def generate_recommendations(
        self,
        analysis: Dict[str, Any],
        event: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations from LLM analysis using ActionMapper

        Args:
            analysis: LLM analysis result
            event: Original incident event

        Returns:
            List of recommendation objects
        """
        # Check if LLM already provided recommendations in new format
        if 'recommendations' in analysis and isinstance(analysis['recommendations'], list):
            # LLM used new structured format - convert to our format
            recommendations = []
            logger.info(f"DEBUG: LLM returned {len(analysis['recommendations'])} recommendations in new format")
            for rec_data in analysis['recommendations']:
                logger.info(f"DEBUG: Processing recommendation: {rec_data}")
                # ActionMapper already validates, just convert format
                raw_action_type = rec_data.get('action_type', 'investigate').upper()

                # Map LLM action types to executor action types
                action_type_map = {
                    'SCALE': 'scale_deployment',
                    'RESTART': 'restart_pods',
                    'ROLLBACK': 'rollback_deployment',
                    'INVESTIGATE': 'investigate'
                }
                action_type = action_type_map.get(raw_action_type, raw_action_type.lower())

                rec = {
                    "type": action_type,
                    "action_type": action_type,  # For auto-response-agent compatibility
                    "action": rec_data.get('rationale', ''),
                    "target": rec_data.get('target_service', 'unknown'),
                    "target_type": rec_data.get('target_type', 'deployment'),
                    "criticality": rec_data.get('criticality', 'medium'),
                    "confidence": analysis.get('confidence', 0),
                    "replicas": rec_data.get('parameters', {}).get('replicas'),
                    "reasoning": rec_data.get('rationale', ''),
                    "parameters": rec_data.get('parameters', {})
                }

                logger.info(f"DEBUG: Converted to: {rec}")
                # Skip INVESTIGATE actions
                if rec['type'] != 'investigate':
                    recommendations.append(rec)
                    logger.info(f"✓ Converted recommendation: {rec['type']} {rec['target']}")
                else:
                    logger.info(f"Skipping INVESTIGATE action: {rec['action']}")

            return recommendations

        # Fallback: Parse from immediate_actions (old format or if new format parsing failed)
        immediate_actions = analysis.get("immediate_actions", [])
        confidence = analysis.get("confidence", 0)

        # Get fallback service from event
        affected_services = event.get("data", {}).get("affected_services", [])
        fallback_service = affected_services[0] if affected_services else "unknown"

        # Use ActionMapper to parse the LLM output
        # Convert analysis back to text for parsing if needed
        llm_text = ""
        if immediate_actions:
            llm_text = "\n".join(immediate_actions)

        # Try to parse recommendations using ActionMapper
        parsed_recommendations = ActionMapper.parse_llm_response(
            llm_output=llm_text,
            fallback_service=fallback_service
        )

        # Convert to dictionary format
        recommendations = []
        for rec in parsed_recommendations:
            rec_dict = rec.to_dict()
            rec_dict['confidence'] = confidence
            recommendations.append(rec_dict)
            logger.debug(f"✓ Parsed recommendation via ActionMapper: {rec.action_type} {rec.target_service}")

        return recommendations

    def _extract_replica_count(self, action_text: str) -> int:
        """Extract replica count from action text"""
        # Look for numbers in action text
        import re
        numbers = re.findall(r'\d+', action_text)
        if numbers:
            return int(numbers[-1])  # Take last number found
        return 5  # Default scale target

    async def publish_analysis(
        self,
        incident_id: str,
        event: Dict[str, Any],
        analysis: Dict[str, Any],
        recommendations: List[Dict[str, Any]]
    ):
        """Publish analysis complete event"""
        analysis_event = {
            "agent": "analyzer",
            "type": "analysis_complete",
            "incident_id": incident_id,
            "timestamp": datetime.utcnow().isoformat(),
            "original_incident": event,
            "analysis": analysis,
            "recommendations": recommendations
        }

        await self.event_publisher.publish(
            routing_key="analyzer.analysis.complete",
            message=analysis_event
        )

        logger.info(
            f"📊 Analysis published: {analysis['root_cause']} | "
            f"Confidence: {analysis['confidence']}% | "
            f"Recommendations: {len(recommendations)}"
        )

    async def publish_analysis_error(
        self,
        incident_id: str,
        event: Dict[str, Any],
        error: str
    ):
        """Publish analysis error event"""
        error_event = {
            "agent": "analyzer",
            "type": "analysis_failed",
            "incident_id": incident_id,
            "timestamp": datetime.utcnow().isoformat(),
            "original_incident": event,
            "error": error
        }

        await self.event_publisher.publish(
            routing_key="analyzer.analysis.failed",
            message=error_event
        )

    async def stop(self):
        """Stop the analyzer agent"""
        logger.info("🛑 Stopping Analyzer Agent...")
        self.running = False
        
        # Cancel queue processor
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        await self.event_consumer.disconnect()
        await self.event_publisher.disconnect()
        logger.info("✓ Analyzer Agent stopped")

    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point"""
    agent = AnalyzerAgent()

    # Setup signal handlers
    signal.signal(signal.SIGINT, agent.handle_signal)
    signal.signal(signal.SIGTERM, agent.handle_signal)

    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
