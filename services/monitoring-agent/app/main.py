"""
Monitoring Agent - Main Entry Point

This agent continuously monitors Prometheus metrics and publishes
incident events when anomalies or threshold breaches are detected.
"""
import asyncio
import logging
import signal
import sys
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict
from aiohttp import web

from app.config import config
from app.prometheus_client import Prometheus
from app.anomaly_detector import AnomalyDetector
from app.event_publisher import EventPublisher
from app.k8s_client import K8sClient
from app.db_client import DatabaseClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitoringAgent:
    """Monitoring Agent - Detects incidents from metrics"""

    def __init__(self):
        self.running = False
        self.monitoring_enabled = False  # Start disabled by default
        self.prometheus = Prometheus(config.prometheus_url)
        self.anomaly_detector = AnomalyDetector(
            sensitivity=config.anomaly_sensitivity,
            min_data_points=config.min_data_points
        )
        self.event_publisher = EventPublisher(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            user=config.rabbitmq_user,
            password=config.rabbitmq_password,
            vhost=config.rabbitmq_vhost,
            exchange=config.rabbitmq_exchange
        )
        self.k8s_client = K8sClient(
            in_cluster=config.k8s_in_cluster,
            namespace=config.k8s_namespace
        )
        self.db_client = DatabaseClient(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password
        )
        self.web_runner = None
        
        # Rate limiting: Track last incident time per metric+service
        self.incident_rate_limiter = defaultdict(float)
        self.rate_limit_window = 10  # seconds between incidents for same metric

        logger.info(f"✓ Monitoring Agent initialized (version {config.agent_version})")
        logger.info(f"⏱️  Rate limiting enabled: {self.rate_limit_window}s between incidents")

    async def start(self):
        """Start the monitoring loop"""
        self.running = True
        logger.info("🚀 Starting Monitoring Agent...")

        # Connect to dependencies
        await self.event_publisher.connect()
        await self.db_client.connect()

        # Start HTTP control server
        await self.start_control_server()

        logger.info(f"📊 Monitoring {len(config.metrics_to_monitor)} metrics")
        logger.info(f"⏰ Check interval: {config.prometheus_scrape_interval}s")
        logger.info(f"🎛️  Monitoring DISABLED by default - call /start to enable")

        # Main monitoring loop
        while self.running:
            try:
                if self.monitoring_enabled:
                    await self.monitor_cycle()
                await asyncio.sleep(config.prometheus_scrape_interval)
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

    async def monitor_cycle(self):
        """Execute one monitoring cycle"""
        logger.debug("Running monitoring cycle...")

        # Check each metric
        for metric in config.metrics_to_monitor:
            try:
                await self.check_metric(metric)
            except Exception as e:
                logger.error(f"Error checking metric {metric}: {e}", exc_info=True)

        # Check Kubernetes pod health
        try:
            await self.check_pod_health()
        except Exception as e:
            logger.error(f"Error checking pod health: {e}")

    async def check_metric(self, metric_name: str):
        """Check a specific metric for anomalies"""
        # Query Prometheus (without namespace filter for non-K8s deployments)
        query = metric_name
        result = await self.prometheus.query(query)

        if not result:
            logger.debug(f"No data for metric: {metric_name}")
            return

        # Process each time series
        for series in result:
            await self.process_metric_series(metric_name, series)

    async def process_metric_series(self, metric_name: str, series: Dict[str, Any]):
        """Process a single metric time series"""
        labels = series.get('metric', {})
        value = float(series.get('value', [None, 0])[1])

        # Build unique identifier for this metric series
        series_id = f"{metric_name}_{labels.get('pod', 'unknown')}"

        # DEBUG: Log every metric check
        logger.info(f"📊 Checking {metric_name} = {value}")

        # Check thresholds
        threshold_breach = self.check_thresholds(metric_name, value, labels)
        if threshold_breach:
            logger.warning(f"🚨 THRESHOLD BREACH: {metric_name} = {value} > {threshold_breach['threshold']}")
            await self.publish_incident(
                incident_type="threshold_breach",
                metric=metric_name,
                value=value,
                labels=labels,
                details=threshold_breach
            )
            return

        # Check for anomalies
        if config.anomaly_detection_enabled:
            is_anomaly = self.anomaly_detector.is_anomaly(series_id, value)
            if is_anomaly:
                await self.publish_incident(
                    incident_type="anomaly_detected",
                    metric=metric_name,
                    value=value,
                    labels=labels,
                    details={"anomaly_score": self.anomaly_detector.get_score(series_id)}
                )

    def check_thresholds(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if metric breaches thresholds"""

        # CPU check
        if "cpu" in metric_name.lower() and value > config.cpu_threshold:
            return {
                "threshold_type": "cpu_high",
                "threshold": config.cpu_threshold,
                "severity": config.severity_mapping.get("cpu_high", "high")
            }

        # Memory check
        if "memory" in metric_name.lower():
            # Convert bytes to percentage if needed
            memory_pct = value  # Simplified - adjust based on your metrics
            if memory_pct > config.memory_threshold:
                return {
                    "threshold_type": "memory_high",
                    "threshold": config.memory_threshold,
                    "severity": config.severity_mapping.get("memory_high", "high")
                }

        # Error rate check
        if "error" in metric_name.lower() and value > config.error_rate_threshold:
            return {
                "threshold_type": "error_rate_high",
                "threshold": config.error_rate_threshold,
                "severity": config.severity_mapping.get("error_rate_high", "critical")
            }

        # Response time check
        if "duration" in metric_name.lower() or "latency" in metric_name.lower():
            if value > (config.response_time_threshold / 1000):  # Convert ms to seconds
                return {
                    "threshold_type": "response_time_slow",
                    "threshold": config.response_time_threshold,
                    "severity": config.severity_mapping.get("response_time_slow", "medium")
                }

        return None

    async def check_pod_health(self):
        """Check Kubernetes pod health"""
        # Skip if K8s client not available (no cluster configured)
        if not self.k8s_client.is_available():
            logger.debug("K8s client not available, skipping pod health check")
            return

        pods = await self.k8s_client.get_pods()

        for pod in pods:
            pod_name = pod.metadata.name
            pod_status = pod.status.phase

            # Check if pod is not running
            if pod_status not in ["Running", "Succeeded"]:
                await self.publish_incident(
                    incident_type="pod_not_running",
                    metric="kube_pod_status",
                    value=0,
                    labels={"pod": pod_name, "status": pod_status},
                    details={
                        "pod_name": pod_name,
                        "status": pod_status,
                        "severity": config.severity_mapping.get("service_down", "critical")
                    }
                )

            # Check restart count
            for container in pod.status.container_statuses or []:
                restart_count = container.restart_count
                if restart_count >= config.pod_restart_threshold:
                    await self.publish_incident(
                        incident_type="pod_restarts",
                        metric="kube_pod_container_status_restarts_total",
                        value=restart_count,
                        labels={
                            "pod": pod_name,
                            "container": container.name
                        },
                        details={
                            "restart_count": restart_count,
                            "threshold": config.pod_restart_threshold,
                            "severity": config.severity_mapping.get("pod_restarts", "medium")
                        }
                    )

    async def publish_incident(
        self,
        incident_type: str,
        metric: str,
        value: float,
        labels: Dict[str, Any],
        details: Dict[str, Any]
    ):
        """Publish an incident event"""
        service_name = labels.get("service", labels.get("pod", "unknown"))
        
        # RATE LIMITING: Prevent incident spam
        rate_limit_key = f"{metric}:{service_name}"
        current_time = time.time()
        last_incident_time = self.incident_rate_limiter.get(rate_limit_key, 0)
        
        if current_time - last_incident_time < self.rate_limit_window:
            time_since_last = int(current_time - last_incident_time)
            logger.debug(
                f"⏱️  Rate limited: {metric} on {service_name} "
                f"(last incident {time_since_last}s ago, min {self.rate_limit_window}s)"
            )
            return
        
        # Check for existing active incident
        active_incident_id = await self.db_client.check_active_incident(metric, service_name)
        
        if active_incident_id:
            logger.debug(f"⏭️ Skipping duplicate incident for {metric} on {service_name} (Active: {active_incident_id})")
            return
        
        # Update rate limiter
        self.incident_rate_limiter[rate_limit_key] = current_time

        incident_id = str(uuid.uuid4())
        severity = details.get("severity", "medium")
        threshold = details.get("threshold")

        logger.info(f"📤 Publishing incident: {incident_type} | {metric} = {value}")

        event = {
            "incident_id": incident_id,
            "agent": "monitoring",
            "event_type": "incident_detected",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "data": {
                "incident_type": incident_type,
                "metric": metric,
                "current_value": value,
                "threshold": threshold,
                "labels": labels,
                "affected_services": [labels.get("service", labels.get("pod", "unknown"))],
                "details": details
            }
        }

        # Store in database
        await self.db_client.store_incident(
            incident_id=incident_id,
            event_type=incident_type,
            severity=severity,
            metric_name=metric,
            metric_value=value,
            threshold=threshold,
            message=f"{incident_type} detected for {metric}",
            labels=labels,
            metadata=event["data"]
        )

        # Publish to RabbitMQ
        await self.event_publisher.publish(
            routing_key="monitoring.incident.detected",
            message=event
        )

        logger.info(
            f"🚨 Incident detected: {incident_type} | "
            f"Metric: {metric} | "
            f"Value: {value} | "
            f"Severity: {event['severity']}"
        )

    async def stop(self):
        """Stop the monitoring agent"""
        logger.info("🛑 Stopping Monitoring Agent...")
        self.running = False
        self.monitoring_enabled = False
        
        # Stop web server
        if self.web_runner:
            await self.web_runner.cleanup()
        
        await self.event_publisher.disconnect()
        await self.db_client.disconnect()
        logger.info("✓ Monitoring Agent stopped")

    async def start_control_server(self):
        """Start HTTP control server for /start and /stop endpoints"""
        app = web.Application()
        app.router.add_post('/start', self.handle_start)
        app.router.add_post('/stop', self.handle_stop)
        app.router.add_get('/status', self.handle_status)
        
        self.web_runner = web.AppRunner(app)
        await self.web_runner.setup()
        site = web.TCPSite(self.web_runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("🌐 Control server started on port 8080")

    async def handle_start(self, request):
        """Enable continuous monitoring"""
        self.monitoring_enabled = True
        logger.info("✅ Monitoring ENABLED")
        return web.json_response({"status": "enabled", "monitoring": True})

    async def handle_stop(self, request):
        """Disable continuous monitoring"""
        self.monitoring_enabled = False
        logger.info("⛔ Monitoring DISABLED")
        return web.json_response({"status": "disabled", "monitoring": False})

    async def handle_status(self, request):
        """Get current monitoring status"""
        return web.json_response({
            "running": self.running,
            "monitoring_enabled": self.monitoring_enabled
        })

    def handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point"""
    agent = MonitoringAgent()

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
