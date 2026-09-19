"""
Slack Client Module

Handles Slack API integration for sending rich notifications.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack API client for sending notifications"""

    def __init__(
        self,
        bot_token: str,
        channel: str,
        username: str = "DevOps Copilot",
        icon_emoji: str = ":robot_face:",
        timeout: int = 10
    ):
        """
        Initialize Slack client

        Args:
            bot_token: Slack bot token
            channel: Default channel for notifications
            username: Bot username
            icon_emoji: Bot icon emoji
            timeout: Request timeout in seconds
        """
        self.bot_token = bot_token
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        self.timeout = timeout

        self.client = AsyncWebClient(token=bot_token, timeout=timeout)
        self.connected = False

    async def connect(self):
        """Test Slack connection"""
        try:
            response = await self.client.auth_test()
            if response["ok"]:
                self.connected = True
                logger.info(f"✓ Slack client connected (team: {response['team']}, user: {response['user']})")
                return True
            else:
                logger.error("Slack auth test failed")
                return False
        except SlackApiError as e:
            logger.error(f"Failed to connect to Slack: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Slack: {e}")
            return False

    async def send_message(
        self,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        Send a message to Slack

        Args:
            text: Plain text message (fallback)
            blocks: Rich message blocks
            channel: Channel to send to (uses default if None)
            thread_ts: Thread timestamp to reply to

        Returns:
            Message timestamp if successful, None otherwise
        """
        if not self.connected:
            logger.warning("Slack client not connected, attempting to connect...")
            await self.connect()

        target_channel = channel or self.channel

        try:
            response = await self.client.chat_postMessage(
                channel=target_channel,
                text=text,
                blocks=blocks,
                username=self.username,
                icon_emoji=self.icon_emoji,
                thread_ts=thread_ts
            )

            if response["ok"]:
                logger.info(f"✓ Sent message to {target_channel}")
                return response["ts"]
            else:
                logger.error(f"Failed to send message: {response.get('error')}")
                return None

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None

    async def send_incident_notification(
        self,
        incident: Dict[str, Any],
        channel: Optional[str] = None
    ) -> Optional[str]:
        """
        Send incident detection notification

        Args:
            incident: Incident details
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        severity = incident.get("severity", "medium").upper()
        metric_name = incident.get("metric_name", "unknown")
        value = incident.get("value", 0)
        threshold = incident.get("threshold", 0)
        target = incident.get("labels", {}).get("pod", "unknown")

        # Severity emoji and color
        severity_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(severity, "⚪")

        color = {
            "CRITICAL": "#FF0000",
            "HIGH": "#FF8C00",
            "MEDIUM": "#FFD700",
            "LOW": "#00FF00"
        }.get(severity, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Incident Detected: {severity}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Metric:*\n{metric_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Target:*\n{target}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Value:*\n{value:.2f}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Threshold:*\n{threshold:.2f}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Incident ID: `{incident.get('incident_id', 'N/A')}`"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Monitoring Agent is analyzing this incident..."
                    }
                ]
            }
        ]

        text = f"{severity_emoji} Incident Detected: {metric_name} on {target} (Value: {value:.2f}, Threshold: {threshold:.2f})"

        return await self.send_message(text=text, blocks=blocks, channel=channel)

    async def send_analysis_notification(
        self,
        incident: Dict[str, Any],
        analysis: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        channel: Optional[str] = None
    ) -> Optional[str]:
        """
        Send analysis completion notification

        Args:
            incident: Incident details
            analysis: Analysis results
            recommendations: Recommended actions
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        incident_id = incident.get("incident_id", "N/A")
        root_cause = analysis.get("root_cause", "Unknown")
        confidence = analysis.get("confidence", 0)

        # Build recommendations text
        rec_text = ""
        for i, rec in enumerate(recommendations[:3], 1):  # Show max 3
            action = rec.get("action_type", "unknown")
            target = rec.get("target", "unknown")
            rec_confidence = rec.get("confidence", 0)
            rec_text += f"{i}. *{action}* on `{target}` (confidence: {rec_confidence}%)\n"

        if len(recommendations) > 3:
            rec_text += f"\n_...and {len(recommendations) - 3} more recommendations_"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 Analysis Complete",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Root Cause Analysis*\n{root_cause}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{confidence}%"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Recommendations:*\n{len(recommendations)} actions"
                    }
                ]
            }
        ]

        if rec_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommended Actions:*\n{rec_text}"
                }
            })

        blocks.extend([
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Incident ID: `{incident_id}`"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Auto-Response Agent is evaluating actions..."
                    }
                ]
            }
        ])

        text = f"🔍 Analysis Complete for incident {incident_id}: {root_cause[:100]}"

        return await self.send_message(text=text, blocks=blocks, channel=channel)

    async def send_action_notification(
        self,
        incident_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        execution_result: Dict[str, Any],
        status: str,
        approval_id: Optional[str] = None,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """
        Send action execution notification

        Args:
            incident_id: Incident ID
            action_type: Type of action
            action_details: Action details
            execution_result: Execution result
            status: Action status
            approval_id: Approval ID if applicable
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        target = action_details.get("target", "unknown")

        # Status emoji and color
        status_emoji = {
            "success": "✅",
            "failed": "❌",
            "dry_run": "🧪",
            "approved": "✅",
            "rejected": "❌",
            "timeout": "⏰"
        }.get(status, "ℹ️")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} Action {status.title()}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Action:*\n{action_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Target:*\n{target}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{status.upper()}"
                    }
                ]
            }
        ]

        # Add execution details
        if execution_result:
            details_text = ""
            if "old_replicas" in execution_result and "new_replicas" in execution_result:
                details_text += f"Replicas: {execution_result['old_replicas']} → {execution_result['new_replicas']}\n"
            if "pods_restarted" in execution_result:
                details_text += f"Pods restarted: {execution_result['pods_restarted']}\n"
            if "error" in execution_result:
                details_text += f"Error: {execution_result['error']}\n"

            if details_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n{details_text}"
                    }
                })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Incident ID: `{incident_id}`" + (f" | Approval ID: `{approval_id}`" if approval_id else "")
                }
            ]
        })

        text = f"{status_emoji} Action {status}: {action_type} on {target}"

        return await self.send_message(text=text, blocks=blocks, channel=channel)

    async def send_approval_request_notification(
        self,
        incident_id: str,
        approval_id: str,
        action_type: str,
        action_details: Dict[str, Any],
        severity: str,
        confidence: int,
        reasoning: str,
        channel: Optional[str] = None
    ) -> Optional[str]:
        """
        Send approval request notification

        Args:
            incident_id: Incident ID
            approval_id: Approval request ID
            action_type: Type of action
            action_details: Action details
            severity: Action severity
            confidence: AI confidence score
            reasoning: Reasoning for action
            channel: Channel to send to

        Returns:
            Message timestamp if successful
        """
        target = action_details.get("target", "unknown")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Approval Required",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Action requires human approval*\n{reasoning}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Action:*\n{action_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Target:*\n{target}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity.upper()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:*\n{confidence}%"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Incident ID: `{incident_id}` | Approval ID: `{approval_id}`"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔗 Go to Approval Dashboard to review this request"
                    }
                ]
            }
        ]

        text = f"⚠️ Approval Required: {action_type} on {target} (Severity: {severity})"

        return await self.send_message(text=text, blocks=blocks, channel=channel)

    async def health_check(self) -> bool:
        """
        Check if Slack client is healthy

        Returns:
            True if connected and working
        """
        if not self.connected:
            return await self.connect()

        try:
            response = await self.client.auth_test()
            return response["ok"]
        except Exception as e:
            logger.warning(f"Slack health check failed: {e}")
            return False
