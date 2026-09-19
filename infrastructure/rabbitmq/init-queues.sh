#!/bin/bash
# ============================================================================
# RabbitMQ Queue Initialization Script
# Description: Creates all required queues, exchanges, and bindings
# ============================================================================

set -e

# Configuration
RABBITMQ_HOST="${RABBITMQ_HOST:-localhost}"
RABBITMQ_PORT="${RABBITMQ_PORT:-15672}"
RABBITMQ_USER="${RABBITMQ_USER:-devops}"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-devops123}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-devops}"
RABBITMQ_API="http://${RABBITMQ_HOST}:${RABBITMQ_PORT}/api"

echo "===================================="
echo "RabbitMQ Queue Initialization"
echo "===================================="
echo "Host: ${RABBITMQ_HOST}:${RABBITMQ_PORT}"
echo "VHost: ${RABBITMQ_VHOST}"
echo "===================================="

# Wait for RabbitMQ to be ready
echo "Waiting for RabbitMQ to be ready..."
until curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" "${RABBITMQ_API}/overview" > /dev/null; do
    echo "RabbitMQ is not ready yet. Retrying in 5 seconds..."
    sleep 5
done
echo "RabbitMQ is ready!"
echo ""

# ============================================================================
# CREATE EXCHANGES
# ============================================================================

echo "Creating exchanges..."

# Main exchange for task routing
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{"type":"topic","durable":true}' \
    "${RABBITMQ_API}/exchanges/${RABBITMQ_VHOST}/devops.tasks"

# Dead letter exchange for failed messages
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{"type":"fanout","durable":true}' \
    "${RABBITMQ_API}/exchanges/${RABBITMQ_VHOST}/devops.dead_letter"

# Notifications exchange
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{"type":"topic","durable":true}' \
    "${RABBITMQ_API}/exchanges/${RABBITMQ_VHOST}/devops.notifications"

echo "Exchanges created successfully!"
echo ""

# ============================================================================
# CREATE QUEUES
# ============================================================================

echo "Creating queues..."

# LLM Tasks Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter",
            "x-message-ttl":3600000,
            "x-max-priority":10
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/llm_tasks"

# Approval Requests Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter",
            "x-message-ttl":7200000,
            "x-max-priority":10
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/approval_requests"

# Email Notifications Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter",
            "x-message-ttl":1800000,
            "x-max-priority":10
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/email_notifications"

# WebSocket Notifications Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":false,
        "arguments":{
            "x-message-ttl":60000,
            "x-max-priority":10
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/websocket_notifications"

# Document Ingestion Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter",
            "x-message-ttl":7200000
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/document_ingestion"

# Batch Processing Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter",
            "x-message-ttl":14400000
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/batch_processing"

# Dead Letter Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/dead_letter_queue"

# Scheduled Tasks Queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "durable":true,
        "arguments":{
            "x-dead-letter-exchange":"devops.dead_letter"
        }
    }' \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}/scheduled_tasks"

echo "Queues created successfully!"
echo ""

# ============================================================================
# CREATE BINDINGS
# ============================================================================

echo "Creating queue bindings..."

# Bind LLM tasks queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"llm.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.tasks/q/llm_tasks"

# Bind approval requests queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"approval.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.tasks/q/approval_requests"

# Bind email notifications queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"notification.email.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.notifications/q/email_notifications"

# Bind websocket notifications queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"notification.websocket.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.notifications/q/websocket_notifications"

# Bind document ingestion queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"document.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.tasks/q/document_ingestion"

# Bind batch processing queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"batch.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.tasks/q/batch_processing"

# Bind scheduled tasks queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{"routing_key":"scheduled.*"}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.tasks/q/scheduled_tasks"

# Bind dead letter queue
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X POST \
    -H "content-type:application/json" \
    -d '{}' \
    "${RABBITMQ_API}/bindings/${RABBITMQ_VHOST}/e/devops.dead_letter/q/dead_letter_queue"

echo "Bindings created successfully!"
echo ""

# ============================================================================
# SET POLICIES
# ============================================================================

echo "Setting queue policies..."

# High availability policy for all queues
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "pattern":".*",
        "definition":{
            "ha-mode":"all",
            "ha-sync-mode":"automatic"
        },
        "priority":0,
        "apply-to":"queues"
    }' \
    "${RABBITMQ_API}/policies/${RABBITMQ_VHOST}/ha-all"

# TTL policy for temporary queues
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    -X PUT \
    -H "content-type:application/json" \
    -d '{
        "pattern":"temp\\..*",
        "definition":{
            "expires":3600000
        },
        "priority":1,
        "apply-to":"queues"
    }' \
    "${RABBITMQ_API}/policies/${RABBITMQ_VHOST}/temp-queue-ttl"

echo "Policies set successfully!"
echo ""

# ============================================================================
# VERIFY SETUP
# ============================================================================

echo "Verifying setup..."
echo ""
echo "Exchanges:"
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    "${RABBITMQ_API}/exchanges/${RABBITMQ_VHOST}" | \
    grep -o '"name":"[^"]*"' | \
    grep "devops" | \
    cut -d'"' -f4

echo ""
echo "Queues:"
curl -sf -u "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
    "${RABBITMQ_API}/queues/${RABBITMQ_VHOST}" | \
    grep -o '"name":"[^"]*"' | \
    cut -d'"' -f4

echo ""
echo "===================================="
echo "RabbitMQ initialization complete!"
echo "===================================="
echo ""
echo "Queue routing keys:"
echo "  LLM Tasks: llm.*"
echo "  Approvals: approval.*"
echo "  Email Notifications: notification.email.*"
echo "  WebSocket Notifications: notification.websocket.*"
echo "  Documents: document.*"
echo "  Batch Jobs: batch.*"
echo "  Scheduled Tasks: scheduled.*"
echo ""
echo "Management UI: http://${RABBITMQ_HOST}:${RABBITMQ_PORT}"
echo "===================================="
