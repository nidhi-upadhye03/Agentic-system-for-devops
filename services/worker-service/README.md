# Worker Service

Background worker service for processing asynchronous tasks using RabbitMQ.

## Features

- **RabbitMQ Integration**: Consumes messages from multiple queues
- **Task Processing**: Handles LLM requests, approvals, and notifications
- **Error Handling**: Automatic retry with exponential backoff
- **Dead Letter Queue**: Failed messages after max retries
- **Database Integration**: PostgreSQL for persistence
- **Graceful Shutdown**: Signal handling for clean termination
- **Health Checks**: Built-in health monitoring

## Architecture

The worker service consists of:

- **main.py**: Entry point with RabbitMQ connection management
- **consumers.py**: Message consumer with error handling and retry logic
- **tasks.py**: Task handlers for different message types
- **config.py**: Configuration management

## Task Types

### 1. LLM Requests (`llm.request.*`)
Processes LLM generation requests by calling the LLM Service API.

### 2. Approval Workflows (`approval.*`)
- `approval.create`: Create new approval records
- `approval.update`: Update approval status (approve/reject)

### 3. Notifications (`notification.*`)
- `notification.email`: Send email notifications
- `notification.slack`: Send Slack notifications

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# PostgreSQL
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=devops_db
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

# LLM Service
LLM_SERVICE_URL=http://localhost:8000

# Email
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
```

## Running the Service

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the worker
python -m app.main
```

### Docker

```bash
# Build image
docker build -t worker-service:latest .

# Run container
docker run -d \
  --name worker-service \
  --env-file .env \
  worker-service:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  worker:
    build: .
    environment:
      RABBITMQ_HOST: rabbitmq
      DATABASE_HOST: postgres
      LLM_SERVICE_URL: http://llm-service:8000
    depends_on:
      - rabbitmq
      - postgres
    restart: unless-stopped
```

## Message Format

### LLM Request Message

```json
{
  "request_id": "req_123",
  "user_id": "user_456",
  "model": "gpt-3.5-turbo",
  "prompt": "Your prompt here",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 100
  },
  "callback_url": "http://example.com/callback"
}
```

### Approval Message

```json
{
  "request_id": "approval_123",
  "user_id": "user_456",
  "request_type": "deployment",
  "request_data": {
    "environment": "production"
  },
  "approvers": ["approver@example.com"]
}
```

### Notification Message

```json
{
  "notification_id": "notif_123",
  "recipient": "user@example.com",
  "subject": "Subject",
  "body": "Message body",
  "html": false
}
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_consumers.py
```

## Error Handling

The worker implements a robust error handling strategy:

1. **Retry Logic**: Failed messages are retried up to `MAX_RETRIES` times
2. **Exponential Backoff**: Delay between retries increases
3. **Dead Letter Queue**: Messages exceeding max retries are moved to DLQ
4. **Error Logging**: All errors are logged with full context

## Monitoring

The service logs important metrics:

- Message processing times
- Success/failure rates
- Queue depths
- Error details

## Database Schema

### approval_records

- `id`: Primary key
- `request_id`: Unique request identifier
- `user_id`: Requesting user
- `request_type`: Type of approval
- `status`: pending/approved/rejected
- `approver_id`: Who approved/rejected
- `created_at`, `updated_at`: Timestamps

### notification_logs

- `id`: Primary key
- `notification_id`: Unique notification identifier
- `notification_type`: email/slack
- `recipient`: Notification recipient
- `status`: pending/sent/failed
- `sent_at`, `created_at`: Timestamps

### llm_request_logs

- `id`: Primary key
- `request_id`: Unique request identifier
- `user_id`: Requesting user
- `model`: LLM model used
- `prompt`: Input prompt
- `response`: Generated response
- `status`: pending/completed/failed
- `tokens_used`: Token consumption
- `processing_time`: Time in milliseconds
- `created_at`, `completed_at`: Timestamps

## License

MIT
