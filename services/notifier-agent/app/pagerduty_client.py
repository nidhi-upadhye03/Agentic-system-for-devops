"""
PagerDuty Client - Trigger and manage incidents via PagerDuty Events API v2

Sends critical incidents to PagerDuty for on-call escalation.
"""
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PagerDutyClient:
    """PagerDuty incident management client using Events API v2"""

    EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"

    def __init__(
        self,
        integration_key: str = "",
        enabled: bool = False
    ):
        """
        Initialize PagerDuty Client

        Args:
            integration_key: PagerDuty Events API v2 integration key
            enabled: Enable PagerDuty notifications
        """
        self.enabled = enabled
        self.integration_key = integration_key

        if self.enabled:
            if not integration_key:
                logger.warning("PagerDuty enabled but integration key missing. Disabling PagerDuty.")
                self.enabled = False
            else:
                logger.info("PagerDuty client initialized")
        else:
            logger.info("PagerDuty notifications disabled")

    async def trigger_incident(
        self,
        incident_data: dict,
        severity: str = "critical",
        dedup_key: Optional[str] = None
    ) -> bool:
        """
        Trigger a PagerDuty incident

        Args:
            incident_data: Incident data dictionary
            severity: Incident severity (maps to PagerDuty severity)
            dedup_key: Deduplication key (optional, uses incident_id if not provided)

        Returns:
            True if triggered successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("PagerDuty notifications disabled, skipping")
            return False

        if not self.integration_key:
            logger.error("PagerDuty integration key not configured")
            return False

        try:
            # Use incident_id as dedup_key if not provided
            if not dedup_key:
                dedup_key = incident_data.get('incident_id', f"devops-{datetime.utcnow().timestamp()}")

            # Map severity to PagerDuty severity levels
            pd_severity = {
                "critical": "critical",
                "high": "error",
                "medium": "warning",
                "low": "info"
            }.get(severity, "error")

            # Build PagerDuty event payload
            payload = {
                "routing_key": self.integration_key,
                "event_action": "trigger",
                "dedup_key": dedup_key,
                "payload": {
                    "summary": incident_data.get('title', 'DevOps Incident')[:1024],
                    "severity": pd_severity,
                    "source": incident_data.get('service', 'devops-copilot'),
                    "timestamp": incident_data.get('timestamp', datetime.utcnow().isoformat()),
                    "component": incident_data.get('component', 'unknown'),
                    "group": incident_data.get('category', 'general'),
                    "class": incident_data.get('metric', 'alert'),
                    "custom_details": {
                        "incident_id": incident_data.get('incident_id', 'N/A'),
                        "description": incident_data.get('description', 'N/A'),
                        "value": incident_data.get('value', 'N/A'),
                        "threshold": incident_data.get('threshold', 'N/A'),
                        "service": incident_data.get('service', 'N/A'),
                        "namespace": incident_data.get('namespace', 'N/A'),
                        "dashboard_url": incident_data.get('dashboard_url', 'http://localhost:3001')
                    }
                },
                "links": [
                    {
                        "href": incident_data.get('dashboard_url', 'http://localhost:3001'),
                        "text": "View Dashboard"
                    }
                ],
                "client": "DevOps Copilot",
                "client_url": incident_data.get('dashboard_url', 'http://localhost:3001')
            }

            # Send to PagerDuty Events API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.EVENTS_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 202:
                    result = response.json()
                    logger.info(f"PagerDuty incident triggered: dedup_key={result.get('dedup_key')}")
                    return True
                else:
                    logger.error(f"PagerDuty API error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to trigger PagerDuty incident: {e}")
            return False

    async def resolve_incident(
        self,
        dedup_key: str,
        incident_data: Optional[dict] = None
    ) -> bool:
        """
        Resolve a PagerDuty incident

        Args:
            dedup_key: Deduplication key of the incident to resolve
            incident_data: Optional incident data for resolution details

        Returns:
            True if resolved successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("PagerDuty notifications disabled, skipping")
            return False

        if not self.integration_key:
            logger.error("PagerDuty integration key not configured")
            return False

        try:
            # Build resolve event payload
            payload = {
                "routing_key": self.integration_key,
                "event_action": "resolve",
                "dedup_key": dedup_key
            }

            # Add resolution details if provided
            if incident_data:
                payload["payload"] = {
                    "summary": f"RESOLVED: {incident_data.get('title', 'Incident')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "custom_details": {
                        "resolution": incident_data.get('resolution', 'Incident resolved automatically'),
                        "resolved_at": datetime.utcnow().isoformat()
                    }
                }

            # Send to PagerDuty Events API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.EVENTS_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 202:
                    logger.info(f"PagerDuty incident resolved: dedup_key={dedup_key}")
                    return True
                else:
                    logger.error(f"PagerDuty API error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to resolve PagerDuty incident: {e}")
            return False

    async def acknowledge_incident(
        self,
        dedup_key: str
    ) -> bool:
        """
        Acknowledge a PagerDuty incident

        Args:
            dedup_key: Deduplication key of the incident to acknowledge

        Returns:
            True if acknowledged successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("PagerDuty notifications disabled, skipping")
            return False

        if not self.integration_key:
            logger.error("PagerDuty integration key not configured")
            return False

        try:
            payload = {
                "routing_key": self.integration_key,
                "event_action": "acknowledge",
                "dedup_key": dedup_key
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.EVENTS_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 202:
                    logger.info(f"PagerDuty incident acknowledged: dedup_key={dedup_key}")
                    return True
                else:
                    logger.error(f"PagerDuty API error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to acknowledge PagerDuty incident: {e}")
            return False

    async def send_incident_alert(
        self,
        incident_data: dict,
        severity: str = "critical"
    ) -> bool:
        """
        Send incident alert via PagerDuty (convenience method)

        Args:
            incident_data: Incident data dictionary
            severity: Incident severity

        Returns:
            True if sent successfully
        """
        # Only trigger PagerDuty for critical incidents (avoid alert fatigue)
        if severity != "critical":
            logger.debug(f"PagerDuty skipped for {severity} severity (only triggers for critical)")
            return False

        return await self.trigger_incident(
            incident_data=incident_data,
            severity=severity
        )

    def is_enabled(self) -> bool:
        """Check if PagerDuty notifications are enabled"""
        return self.enabled
