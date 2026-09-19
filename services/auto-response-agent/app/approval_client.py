"""
Approval Client Module

Integrates with Approval Dashboard API to request human approvals
for critical actions and wait for responses.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class ApprovalClient:
    """Client for Approval Dashboard API"""

    def __init__(
        self,
        api_url: str,
        timeout: int = 300,
        poll_interval: int = 5
    ):
        """
        Initialize approval client

        Args:
            api_url: Approval Dashboard API base URL
            timeout: Maximum time to wait for approval (seconds)
            poll_interval: How often to check approval status (seconds)
        """
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        logger.info(f"✓ Approval client connected to {self.api_url}")

    async def disconnect(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("✓ Approval client disconnected")

    async def create_approval_request(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        severity: str,
        confidence: int,
        reasoning: str
    ) -> Dict[str, Any]:
        """
        Create an approval request in the dashboard

        Args:
            incident_id: Associated incident ID
            action_type: Type of action (scale, restart, rollback, etc.)
            action_details: Full action details
            severity: Action severity (low, medium, high, critical)
            confidence: AI confidence score (0-100)
            reasoning: Explanation for the action

        Returns:
            Created approval record with ID
        """
        if not self.session:
            raise RuntimeError("Approval client not connected")

        # Map action_type to valid request_type (database constraint)
        request_type_mapping = {
            "scale_deployment": "scaling",
            "restart_pods": "infrastructure", 
            "rollback_deployment": "deployment",
            "adjust_resources": "configuration"
        }
        request_type = request_type_mapping.get(action_type, "other")
        
        payload = {
            "title": f"{severity.upper()}: {action_type} on {action_details.get('target', 'unknown')}",
            "description": reasoning or f"Automated recommendation: {action_type}",
            "request_type": request_type,  # Use valid DB constraint value
            "priority": severity if severity in ["low", "medium", "high", "critical"] else "medium",
            "metadata": {
                "incident_id": incident_id,
                "action_type": action_type,
                "action_details": action_details,
                "confidence": confidence,
                "severity": severity,
                "timeout_seconds": self.timeout
            }
        }

        try:
            logger.debug(f"Posting approval request to {self.api_url}/approvals: {payload}")
            async with self.session.post(
                f"{self.api_url}/approvals",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 201 or response.status == 200:
                    result = await response.json()
                    logger.info(f"API Response: {result}")
                    # Extract ID from {"success": true, "data": {"id": 91, ...}}
                    if isinstance(result, dict) and "data" in result:
                        approval_data = result["data"]
                        approval_id = approval_data.get("id") or approval_data.get("approval_id")
                    else:
                        approval_id = result.get("id") or result.get("approval_id")
                    logger.info(f"✓ Created approval request: {approval_id}")
                    return approval_id
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create approval request: {response.status} - {error_text}")
                    raise RuntimeError(f"Approval API error: {response.status}")

        except asyncio.TimeoutError:
            logger.error("Timeout creating approval request")
            raise
        except Exception as e:
            logger.error(f"Error creating approval request: {e}")
            raise

    async def wait_for_approval(
        self,
        approval_id: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Wait for approval decision (polling-based)

        Args:
            approval_id: Approval record ID
            timeout: Override default timeout (seconds)

        Returns:
            Approval decision with status and comments
        """
        if not self.session:
            raise RuntimeError("Approval client not connected")

        wait_timeout = timeout or self.timeout
        start_time = asyncio.get_event_loop().time()

        logger.info(f"⏳ Waiting for approval {approval_id} (timeout: {wait_timeout}s)")

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time

            # Check timeout
            if elapsed >= wait_timeout:
                logger.warning(f"Approval {approval_id} timed out after {wait_timeout}s")
                return {
                    "approved": False,
                    "status": "timeout",
                    "message": f"No decision received within {wait_timeout} seconds"
                }

            # Poll approval status
            try:
                approval = await self.get_approval_status(approval_id)
                status = approval.get("status", "pending")

                if status == "approved":
                    logger.info(f"✓ Approval {approval_id} APPROVED")
                    return {
                        "approved": True,
                        "status": "approved",
                        "approved_by": approval.get("approved_by"),
                        "approved_at": approval.get("approved_at"),
                        "comments": approval.get("comments"),
                        "message": "Action approved by human"
                    }

                elif status == "rejected":
                    logger.info(f"✗ Approval {approval_id} REJECTED")
                    return {
                        "approved": False,
                        "status": "rejected",
                        "rejected_by": approval.get("rejected_by"),
                        "rejected_at": approval.get("rejected_at"),
                        "comments": approval.get("comments"),
                        "message": "Action rejected by human"
                    }

                elif status == "pending":
                    # Still waiting
                    logger.debug(f"Approval {approval_id} still pending... ({elapsed:.0f}s elapsed)")
                    await asyncio.sleep(self.poll_interval)

                else:
                    logger.warning(f"Unknown approval status: {status}")
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Error polling approval status: {e}")
                await asyncio.sleep(self.poll_interval)

    async def get_approval_status(self, approval_id: str) -> Dict[str, Any]:
        """
        Get current approval status

        Args:
            approval_id: Approval record ID

        Returns:
            Current approval record
        """
        if not self.session:
            raise RuntimeError("Approval client not connected")

        try:
            async with self.session.get(
                f"{self.api_url}/approvals/{approval_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get approval status: {response.status}")
                    raise RuntimeError(f"Approval API error: {response.status}")

        except Exception as e:
            logger.error(f"Error getting approval status: {e}")
            raise

    async def cancel_approval(self, approval_id: str) -> bool:
        """
        Cancel a pending approval request

        Args:
            approval_id: Approval record ID

        Returns:
            True if cancelled successfully
        """
        if not self.session:
            raise RuntimeError("Approval client not connected")

        try:
            async with self.session.delete(
                f"{self.api_url}/approvals/{approval_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    logger.info(f"✓ Cancelled approval {approval_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel approval: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error cancelling approval: {e}")
            return False

    async def update_approval_progress(
        self,
        approval_id: str,
        progress: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update approval request with execution progress

        Args:
            approval_id: Approval record ID
            progress: Progress message
            metadata: Additional metadata

        Returns:
            True if updated successfully
        """
        if not self.session:
            raise RuntimeError("Approval client not connected")

        payload = {
            "progress": progress,
            "updated_at": datetime.utcnow().isoformat()
        }

        if metadata:
            payload["metadata"] = metadata

        try:
            async with self.session.patch(
                f"{self.api_url}/approvals/{approval_id}",
                json=update_data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    logger.debug(f"✓ Updated approval {approval_id} progress")
                    return True
                else:
                    logger.warning(f"Failed to update approval progress: {response.status}")
                    return False

        except Exception as e:
            logger.warning(f"Error updating approval progress: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if Approval Dashboard API is reachable

        Returns:
            True if healthy
        """
        if not self.session:
            return False

        try:
            async with self.session.get(
                f"{self.api_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.warning(f"Approval API health check failed: {e}")
            return False
