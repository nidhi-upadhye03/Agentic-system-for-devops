"""
Email Client - Send email notifications

Supports SMTP and SendGrid for sending alert emails.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailClient:
    """Email notification client"""

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_email: str = "",
        enabled: bool = False
    ):
        """
        Initialize Email Client

        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            enabled: Enable email notifications
        """
        self.enabled = enabled
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email or smtp_user

        if self.enabled:
            if not all([smtp_host, smtp_user, smtp_password]):
                logger.warning("Email enabled but credentials missing. Disabling email notifications.")
                self.enabled = False
            else:
                logger.info(f"Email client initialized: {self.from_email} via {self.smtp_host}:{self.smtp_port}")
        else:
            logger.info("Email notifications disabled")

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> bool:
        """
        Send email notification

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            cc_emails: CC recipients (optional)
            priority: Email priority (low, normal, high, critical)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled, skipping")
            return False

        if not to_emails:
            logger.warning("No recipient emails provided")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[DevOps Alert] {subject}"
            msg['Date'] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)

            # Set priority
            if priority == "critical":
                msg['X-Priority'] = '1'
                msg['Importance'] = 'high'
            elif priority == "high":
                msg['X-Priority'] = '2'
                msg['Importance'] = 'high'

            # Attach text body
            text_part = MIMEText(body_text, 'plain')
            msg.attach(text_part)

            # Attach HTML body if provided
            if body_html:
                html_part = MIMEText(body_html, 'html')
                msg.attach(html_part)

            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)

                all_recipients = to_emails + (cc_emails or [])
                server.sendmail(self.from_email, all_recipients, msg.as_string())

            logger.info(f"Email sent: '{subject}' to {len(to_emails)} recipients")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_incident_alert(
        self,
        incident_data: dict,
        to_emails: List[str],
        severity: str = "medium"
    ) -> bool:
        """
        Send incident alert email

        Args:
            incident_data: Incident data dictionary
            to_emails: Recipients
            severity: Incident severity

        Returns:
            True if sent successfully
        """
        subject = f"{severity.upper()}: {incident_data.get('title', 'Incident Detected')}"

        # Plain text body
        body_text = f"""
DevOps Copilot Incident Alert

INCIDENT DETAILS
================================================================================
Title: {incident_data.get('title', 'N/A')}
Severity: {severity.upper()}
Incident ID: {incident_data.get('incident_id', 'N/A')}
Timestamp: {incident_data.get('timestamp', 'N/A')}

Service: {incident_data.get('service', 'N/A')}
Metric: {incident_data.get('metric', 'N/A')}
Current Value: {incident_data.get('value', 'N/A')}
Threshold: {incident_data.get('threshold', 'N/A')}

Description:
{incident_data.get('description', 'N/A')}

================================================================================
View details: {incident_data.get('dashboard_url', 'http://localhost:3001')}

This is an automated alert from DevOps Copilot.
"""

        # HTML body
        severity_color = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#f59e0b",
            "low": "#84cc16"
        }.get(severity, "#6b7280")

        body_html = f"""
<html>
<head>
<style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
    .header {{ background: {severity_color}; color: white; padding: 20px; }}
    .content {{ padding: 20px; }}
    .detail {{ margin: 10px 0; }}
    .label {{ font-weight: bold; color: #374151; }}
    .value {{ color: #111827; }}
    .footer {{ background: #f3f4f6; padding: 15px; margin-top: 20px; font-size: 12px; color: #6b7280; }}
    .button {{ background: {severity_color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; }}
</style>
</head>
<body>
    <div class="header">
        <h2 style="margin:0;">[{severity.upper()}] {incident_data.get('title', 'Incident Detected')}</h2>
    </div>
    <div class="content">
        <div class="detail">
            <span class="label">Incident ID:</span> <span class="value">{incident_data.get('incident_id', 'N/A')}</span>
        </div>
        <div class="detail">
            <span class="label">Service:</span> <span class="value">{incident_data.get('service', 'N/A')}</span>
        </div>
        <div class="detail">
            <span class="label">Metric:</span> <span class="value">{incident_data.get('metric', 'N/A')}</span>
        </div>
        <div class="detail">
            <span class="label">Current Value:</span> <span class="value">{incident_data.get('value', 'N/A')}</span>
        </div>
        <div class="detail">
            <span class="label">Threshold:</span> <span class="value">{incident_data.get('threshold', 'N/A')}</span>
        </div>
        <div class="detail">
            <span class="label">Description:</span><br>
            <p class="value">{incident_data.get('description', 'N/A')}</p>
        </div>
        <p>
            <a href="{incident_data.get('dashboard_url', 'http://localhost:3001')}" class="button">View Dashboard</a>
        </p>
    </div>
    <div class="footer">
        This is an automated alert from DevOps Copilot.<br>
        Timestamp: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
    </div>
</body>
</html>
"""

        return await self.send_email(
            to_emails=to_emails,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            priority=severity
        )

    def is_enabled(self) -> bool:
        """Check if email notifications are enabled"""
        return self.enabled
