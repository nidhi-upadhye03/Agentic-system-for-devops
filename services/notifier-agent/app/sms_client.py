"""
SMS Client - Send SMS notifications via Twilio

Sends critical alerts via SMS for immediate attention.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SMSClient:
    """SMS notification client using Twilio"""

    def __init__(
        self,
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "",
        enabled: bool = False
    ):
        """
        Initialize SMS Client

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number (sender)
            enabled: Enable SMS notifications
        """
        self.enabled = enabled
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.client = None

        if self.enabled:
            if not all([account_sid, auth_token, from_number]):
                logger.warning("SMS enabled but Twilio credentials missing. Disabling SMS notifications.")
                self.enabled = False
            else:
                try:
                    from twilio.rest import Client
                    self.client = Client(account_sid, auth_token)
                    logger.info(f"SMS client initialized: {from_number}")
                except ImportError:
                    logger.warning("Twilio library not installed. Run: pip install twilio")
                    self.enabled = False
                except Exception as e:
                    logger.error(f"Failed to initialize Twilio client: {e}")
                    self.enabled = False
        else:
            logger.info("SMS notifications disabled")

    async def send_sms(
        self,
        to_numbers: List[str],
        message: str,
        priority: str = "normal"
    ) -> bool:
        """
        Send SMS notification

        Args:
            to_numbers: List of recipient phone numbers (E.164 format: +1234567890)
            message: SMS message text (max 160 characters recommended)
            priority: Message priority (only sends if critical or high)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("SMS notifications disabled, skipping")
            return False

        if not to_numbers:
            logger.warning("No recipient phone numbers provided")
            return False

        # Only send SMS for critical/high priority (avoid SMS spam)
        if priority not in ["critical", "high"]:
            logger.debug(f"SMS skipped for {priority} priority (only sends for critical/high)")
            return False

        if not self.client:
            logger.error("Twilio client not initialized")
            return False

        try:
            # Truncate message to 160 characters for standard SMS
            if len(message) > 160:
                message = message[:157] + "..."
                logger.warning("Message truncated to 160 characters for SMS")

            sent_count = 0
            failed_count = 0

            for to_number in to_numbers:
                try:
                    # Validate phone number format
                    if not to_number.startswith('+'):
                        logger.warning(f"Invalid phone number format (must start with +): {to_number}")
                        failed_count += 1
                        continue

                    # Send SMS
                    msg = self.client.messages.create(
                        body=f"[DevOps Alert] {message}",
                        from_=self.from_number,
                        to=to_number
                    )

                    logger.info(f"SMS sent to {to_number}: SID={msg.sid}")
                    sent_count += 1

                except Exception as e:
                    logger.error(f"Failed to send SMS to {to_number}: {e}")
                    failed_count += 1

            logger.info(f"SMS delivery: {sent_count} sent, {failed_count} failed")
            return sent_count > 0

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    async def send_incident_alert(
        self,
        incident_data: dict,
        to_numbers: List[str],
        severity: str = "medium"
    ) -> bool:
        """
        Send incident alert via SMS

        Args:
            incident_data: Incident data dictionary
            to_numbers: Recipient phone numbers
            severity: Incident severity

        Returns:
            True if sent successfully
        """
        # Format short message for SMS
        title = incident_data.get('title', 'Incident')[:50]
        service = incident_data.get('service', 'N/A')[:20]

        message = f"{severity.upper()}: {title} | Service: {service}"

        return await self.send_sms(
            to_numbers=to_numbers,
            message=message,
            priority=severity
        )

    def is_enabled(self) -> bool:
        """Check if SMS notifications are enabled"""
        return self.enabled
