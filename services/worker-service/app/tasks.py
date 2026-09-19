"""
Task Definitions
Handles processing of LLM requests, approval workflows, and notifications
"""

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, Coroutine, Dict, Optional
from pika.spec import BasicProperties

import httpx
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine(settings.DATABASE_URL, pool_size=settings.DATABASE_POOL_SIZE)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Database Models
class ApprovalRecord(Base):
    """Approval record model."""
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(255), nullable=False)
    request_type = Column(String(100), nullable=False)
    request_data = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    approver_id = Column(String(255), nullable=True)
    approval_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationLog(Base):
    """Notification log model."""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(255), unique=True, index=True, nullable=False)
    notification_type = Column(String(100), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMRequestLog(Base):
    """LLM request log model."""
    __tablename__ = "llm_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(255), nullable=False)
    model = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)


@dataclass
class TaskContext:
    """Context for task execution."""
    routing_key: str
    message: Dict[str, Any]
    retry_count: int
    properties: BasicProperties


class TaskRegistry:
    """Registry for task handlers."""

    def __init__(self):
        self.handlers: Dict[str, Callable[[TaskContext], Coroutine]] = {
            'llm_request': process_llm_request,
            'approval_create': process_approval_create,
            'approval_update': process_approval_update,
            'notification_email': process_email_notification,
            'notification_slack': process_slack_notification,
        }

    def get_handler(self, task_type: str) -> Optional[Callable[[TaskContext], Coroutine]]:
        """Get handler for task type."""
        return self.handlers.get(task_type)

    def register(self, task_type: str, handler: Callable[[TaskContext], Coroutine]):
        """Register a new handler."""
        self.handlers[task_type] = handler


# Task Handlers

async def process_llm_request(context: TaskContext):
    """Process LLM request by calling LLM service."""
    message = context.message
    request_id = message.get('request_id')
    user_id = message.get('user_id')
    model = message.get('model', 'gpt-3.5-turbo')
    prompt = message.get('prompt')
    parameters = message.get('parameters', {})

    logger.info(f"Processing LLM request: {request_id}")

    # Create database session
    db = SessionLocal()
    start_time = datetime.utcnow()

    try:
        # Log request to database
        llm_log = LLMRequestLog(
            request_id=request_id,
            user_id=user_id,
            model=model,
            prompt=prompt,
            status='processing'
        )
        db.add(llm_log)
        db.commit()

        # Call LLM service
        async with httpx.AsyncClient(timeout=settings.LLM_SERVICE_TIMEOUT) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/api/v1/generate",
                json={
                    'model': model,
                    'prompt': prompt,
                    'parameters': parameters
                },
                headers={
                    'X-User-ID': user_id,
                    'X-Request-ID': request_id
                }
            )
            response.raise_for_status()
            result = response.json()

        # Update log with response
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        llm_log.response = result.get('response')
        llm_log.status = 'completed'
        llm_log.tokens_used = result.get('tokens_used')
        llm_log.processing_time = processing_time
        llm_log.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"LLM request completed: {request_id} ({processing_time}ms)")

        # Send completion notification if callback URL provided
        callback_url = message.get('callback_url')
        if callback_url:
            await send_callback(callback_url, {
                'request_id': request_id,
                'status': 'completed',
                'result': result
            })

    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling LLM service: {e}")
        llm_log.status = 'failed'
        llm_log.error_message = str(e)
        db.commit()
        raise

    except Exception as e:
        logger.error(f"Error processing LLM request: {e}", exc_info=True)
        llm_log.status = 'failed'
        llm_log.error_message = str(e)
        db.commit()
        raise

    finally:
        db.close()


async def process_approval_create(context: TaskContext):
    """Create approval record."""
    message = context.message
    request_id = message.get('request_id')
    user_id = message.get('user_id')
    request_type = message.get('request_type')
    request_data = message.get('request_data', '')

    logger.info(f"Creating approval record: {request_id}")

    db = SessionLocal()
    try:
        # Create approval record
        approval = ApprovalRecord(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            request_data=str(request_data),
            status='pending'
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        logger.info(f"Approval record created: {request_id}")

        # Send notification to approvers
        approvers = message.get('approvers', [])
        if approvers:
            await notify_approvers(request_id, request_type, approvers)

    except Exception as e:
        logger.error(f"Error creating approval record: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


async def process_approval_update(context: TaskContext):
    """Update approval record."""
    message = context.message
    request_id = message.get('request_id')
    approver_id = message.get('approver_id')
    status = message.get('status')
    comment = message.get('comment', '')

    logger.info(f"Updating approval record: {request_id} -> {status}")

    db = SessionLocal()
    try:
        # Find and update approval record
        approval = db.query(ApprovalRecord).filter(
            ApprovalRecord.request_id == request_id
        ).first()

        if not approval:
            logger.error(f"Approval record not found: {request_id}")
            return

        approval.status = status
        approval.approver_id = approver_id
        approval.approval_comment = comment
        approval.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Approval record updated: {request_id}")

        # Notify requester
        await notify_approval_decision(approval.user_id, request_id, status, comment)

    except Exception as e:
        logger.error(f"Error updating approval record: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


async def process_email_notification(context: TaskContext):
    """Send email notification."""
    message = context.message
    notification_id = message.get('notification_id')
    recipient = message.get('recipient')
    subject = message.get('subject')
    body = message.get('body')
    html = message.get('html', False)

    logger.info(f"Sending email notification: {notification_id} to {recipient}")

    db = SessionLocal()
    try:
        # Log notification
        notification = NotificationLog(
            notification_id=notification_id,
            notification_type='email',
            recipient=recipient,
            subject=subject,
            message=body,
            status='sending'
        )
        db.add(notification)
        db.commit()

        # Send email
        await send_email(recipient, subject, body, html)

        # Update log
        notification.status = 'sent'
        notification.sent_at = datetime.utcnow()
        db.commit()

        logger.info(f"Email sent successfully: {notification_id}")

    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        notification.status = 'failed'
        notification.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


async def process_slack_notification(context: TaskContext):
    """Send Slack notification."""
    message = context.message
    notification_id = message.get('notification_id')
    channel = message.get('channel')
    text = message.get('text')
    blocks = message.get('blocks')

    logger.info(f"Sending Slack notification: {notification_id} to {channel}")

    if not settings.SLACK_ENABLED or not settings.SLACK_WEBHOOK_URL:
        logger.warning("Slack notifications not enabled")
        return

    db = SessionLocal()
    try:
        # Log notification
        notification = NotificationLog(
            notification_id=notification_id,
            notification_type='slack',
            recipient=channel,
            message=text,
            status='sending'
        )
        db.add(notification)
        db.commit()

        # Send to Slack
        payload = {'text': text}
        if blocks:
            payload['blocks'] = blocks

        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json=payload
            )
            response.raise_for_status()

        # Update log
        notification.status = 'sent'
        notification.sent_at = datetime.utcnow()
        db.commit()

        logger.info(f"Slack notification sent successfully: {notification_id}")

    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}", exc_info=True)
        notification.status = 'failed'
        notification.error_message = str(e)
        db.commit()
        raise
    finally:
        db.close()


# Helper Functions

async def send_email(recipient: str, subject: str, body: str, html: bool = False):
    """Send email using SMTP."""
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg['To'] = recipient
    msg['Subject'] = subject

    if html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))

    # Send email in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_email_sync, msg, recipient)


def _send_email_sync(msg: MIMEMultipart, recipient: str):
    """Synchronous email sending."""
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        raise


async def send_callback(callback_url: str, data: Dict[str, Any]):
    """Send callback to webhook URL."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(callback_url, json=data)
            response.raise_for_status()
            logger.info(f"Callback sent successfully to {callback_url}")
    except Exception as e:
        logger.error(f"Failed to send callback to {callback_url}: {e}")


async def notify_approvers(request_id: str, request_type: str, approvers: list):
    """Notify approvers about pending approval."""
    for approver in approvers:
        subject = f"Approval Required: {request_type}"
        body = f"""
        A new approval request requires your attention.

        Request ID: {request_id}
        Type: {request_type}

        Please review and approve/reject this request.
        """

        # Send email notification
        try:
            await send_email(approver, subject, body)
        except Exception as e:
            logger.error(f"Failed to notify approver {approver}: {e}")


async def notify_approval_decision(user_id: str, request_id: str, status: str, comment: str):
    """Notify user about approval decision."""
    subject = f"Approval {status.upper()}: {request_id}"
    body = f"""
    Your approval request has been {status}.

    Request ID: {request_id}
    Status: {status}
    Comment: {comment}
    """

    try:
        await send_email(user_id, subject, body)
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
