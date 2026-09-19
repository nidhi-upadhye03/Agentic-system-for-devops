# Monitoring Agent

**Autonomous DevOps Copilot - Monitoring Agent**

The Monitoring Agent continuously monitors Prometheus metrics and Kubernetes pod health, detecting anomalies and threshold breaches. When incidents are detected, it publishes events to RabbitMQ for downstream processing by other agents.

---

## Features

- **Prometheus Integration**: Query and analyze metrics from Prometheus
- **Kubernetes Monitoring**: Check pod health, restart counts, and deployment status
- **Anomaly Detection**: Statistical Z-score based anomaly detection
- **Threshold Monitoring**: Configurable thresholds for CPU, memory, error rate, response time
- **Event Publishing**: Publish incidents to RabbitMQ for downstream agents
- **Async Architecture**: High-performance async/await implementation
- **Graceful Shutdown**: Handle SIGINT/SIGTERM signals properly

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING AGENT                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Prometheus   │  │ Kubernetes   │  │ Anomaly         │ │
│  │ Client       │  │ Client       │  │ Detector        │ │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘ │
│         │                 │                    │          │
│         └─────────────────┴────────────────────┘          │
│                           │                               │
│                  ┌────────▼─────────┐                     │
│                  │   Main Logic     │                     │
│                  │  - Check Metrics │                     │
│                  │  - Check Pods    │                     │
│                  │  - Detect Issues │                     │
│                  └────────┬─────────┘                     │
│                           │                               │
│                  ┌────────▼─────────┐                     │
│                  │ Event Publisher  │                     │
│                  │   (RabbitMQ)     │                     │
│                  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    RabbitMQ Exchange
                   (agent_events topic)
                           │
                           ▼
                   Downstream Agents
               (Analyzer, Auto-Response, etc.)
```

---

## Modules

### 1. `main.py`
Main entry point and monitoring loop logic.

**Key Classes:**
- `MonitoringAgent`: Core agent orchestrator
  - `start()`: Start monitoring loop
  - `monitor_cycle()`: Execute one monitoring cycle
  - `check_metric()`: Check individual metrics
  - `check_pod_health()`: Check Kubernetes pod health
  - `publish_incident()`: Publish incident events

### 2. `config.py`
Configuration management using Pydantic Settings.

**Environment Variables:**
- `MONITORING_PROMETHEUS_URL`: Prometheus server URL
- `MONITORING_RABBITMQ_HOST`: RabbitMQ host
- `MONITORING_CPU_THRESHOLD`: CPU threshold (default: 80%)
- `MONITORING_MEMORY_THRESHOLD`: Memory threshold (default: 85%)
- See config.py for complete list

### 3. `prometheus_client.py`
Async Prometheus client for querying metrics.

**Key Methods:**
- `query(query_string)`: Execute instant query
- `query_range(query, start, end, step)`: Execute range query
- `get_metric_labels(metric)`: Get metric labels
- `health_check()`: Check Prometheus health

### 4. `k8s_client.py`
Kubernetes API client for cluster resources.

**Key Methods:**
- `get_pods(namespace)`: Get all pods
- `get_pod_status(pod_name)`: Get pod details
- `get_deployments()`: Get deployments
- `get_services()`: Get services
- `health_check()`: Check K8s API access

### 5. `anomaly_detector.py`
Statistical anomaly detection using Z-score method.

**Key Methods:**
- `is_anomaly(series_id, value)`: Check if value is anomalous
- `add_data_point(series_id, value)`: Add historical data
- `get_score(series_id)`: Get anomaly score
- `get_statistics(series_id)`: Get statistical summary

### 6. `event_publisher.py`
RabbitMQ event publisher for incident notifications.

**Key Methods:**
- `connect()`: Connect to RabbitMQ
- `publish(routing_key, message)`: Publish event
- `disconnect()`: Disconnect gracefully
- `health_check()`: Check RabbitMQ connection

---

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Prometheus
MONITORING_PROMETHEUS_URL=http://prometheus:9090
MONITORING_PROMETHEUS_SCRAPE_INTERVAL=30

# Kubernetes
MONITORING_K8S_IN_CLUSTER=false
MONITORING_K8S_NAMESPACE=ai-system

# RabbitMQ
MONITORING_RABBITMQ_HOST=rabbitmq
MONITORING_RABBITMQ_PORT=5672
MONITORING_RABBITMQ_USER=devops
MONITORING_RABBITMQ_PASSWORD=devops123
MONITORING_RABBITMQ_VHOST=devops
MONITORING_RABBITMQ_EXCHANGE=agent_events

# Redis
MONITORING_REDIS_HOST=redis
MONITORING_REDIS_PORT=6379
MONITORING_REDIS_PASSWORD=redis123

# PostgreSQL
MONITORING_POSTGRES_HOST=postgres
MONITORING_POSTGRES_PORT=5432
MONITORING_POSTGRES_DB=devops_db
MONITORING_POSTGRES_USER=devops
MONITORING_POSTGRES_PASSWORD=devops123

# Thresholds
MONITORING_CPU_THRESHOLD=80.0
MONITORING_MEMORY_THRESHOLD=85.0
MONITORING_ERROR_RATE_THRESHOLD=5.0
MONITORING_POD_RESTART_THRESHOLD=3
MONITORING_RESPONSE_TIME_THRESHOLD=2000.0

# Anomaly Detection
MONITORING_ANOMALY_DETECTION_ENABLED=true
MONITORING_ANOMALY_SENSITIVITY=2.0
MONITORING_MIN_DATA_POINTS=10

# Logging
MONITORING_LOG_LEVEL=INFO
MONITORING_ENVIRONMENT=development
```

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Local Development (without Kubernetes)

Set `MONITORING_K8S_IN_CLUSTER=false` and ensure you have kubeconfig configured, or the K8s client will gracefully disable K8s features.

### 3. In-Cluster Deployment

Set `MONITORING_K8S_IN_CLUSTER=true` when deploying to Kubernetes.

---

## Running

### Local Development

```bash
# Set environment variables
export MONITORING_PROMETHEUS_URL=http://localhost:9090
export MONITORING_RABBITMQ_HOST=localhost
export MONITORING_K8S_IN_CLUSTER=false

# Run agent
python app/main.py
```

### Docker

```bash
# Build image
docker build -t monitoring-agent:latest .

# Run container
docker run -d \
  --name monitoring-agent \
  -e MONITORING_PROMETHEUS_URL=http://prometheus:9090 \
  -e MONITORING_RABBITMQ_HOST=rabbitmq \
  monitoring-agent:latest
```

### Docker Compose

```yaml
monitoring-agent:
  build: ./services/monitoring-agent
  environment:
    MONITORING_PROMETHEUS_URL: http://prometheus:9090
    MONITORING_RABBITMQ_HOST: rabbitmq
    MONITORING_K8S_IN_CLUSTER: "false"
  depends_on:
    - prometheus
    - rabbitmq
  networks:
    - devops-network
```

---

## Event Format

When an incident is detected, the agent publishes an event to RabbitMQ:

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent": "monitoring",
  "event_type": "incident_detected",
  "timestamp": "2025-10-22T12:34:56.789Z",
  "severity": "high",
  "data": {
    "incident_type": "threshold_breach",
    "metric": "container_cpu_usage_seconds_total",
    "current_value": 95.3,
    "threshold": 80.0,
    "labels": {
      "pod": "llm-service-abc123",
      "namespace": "ai-system",
      "container": "llm-service"
    },
    "affected_services": ["llm-service"],
    "details": {
      "threshold_type": "cpu_high",
      "threshold": 80.0,
      "severity": "high"
    }
  }
}
```

### Routing Keys

Events are published with topic-based routing keys:

- `monitoring.incident.detected` - Incident detected
- `monitoring.health.degraded` - Service health degraded
- `monitoring.pod.restarted` - Pod restart detected

---

## Monitoring Metrics

Default metrics monitored:

1. **CPU Usage**: `container_cpu_usage_seconds_total`
2. **Memory Usage**: `container_memory_working_set_bytes`
3. **HTTP Requests**: `http_requests_total`
4. **Request Duration**: `http_request_duration_seconds`
5. **Pod Restarts**: `kube_pod_container_status_restarts_total`

Configure custom metrics via `MONITORING_METRICS_TO_MONITOR` environment variable.

---

## Testing

### Unit Tests

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Manual Testing

```bash
# Test Prometheus connection
python -c "
import asyncio
from app.prometheus_client import Prometheus
async def test():
    prom = Prometheus('http://localhost:9090')
    result = await prom.query('up')
    print(result)
asyncio.run(test())
"

# Test RabbitMQ connection
python -c "
import asyncio
from app.event_publisher import EventPublisher
async def test():
    pub = EventPublisher(host='localhost')
    await pub.connect()
    await pub.publish('test.event', {'message': 'hello'})
    await pub.disconnect()
asyncio.run(test())
"
```

---

## Troubleshooting

### Issue: "Failed to connect to Prometheus"
- Ensure Prometheus is running on the configured URL
- Check network connectivity
- Verify firewall rules

### Issue: "K8s client not available"
- Set `MONITORING_K8S_IN_CLUSTER=false` for local dev
- Ensure kubeconfig is properly configured
- K8s features will gracefully disable if not available

### Issue: "RabbitMQ connection failed"
- Verify RabbitMQ is running
- Check credentials and vhost
- Ensure exchange `agent_events` exists

### Issue: "No metrics returned"
- Verify namespace is correct
- Check Prometheus scrape targets
- Ensure metrics exist in Prometheus

---

## Development

### Adding New Metrics

1. Add metric name to `config.py`:
```python
metrics_to_monitor: List[str] = Field(
    default=[
        "your_new_metric_name",
        ...
    ]
)
```

2. Add threshold logic in `main.py` `check_thresholds()` method.

### Adding New Anomaly Methods

Extend `anomaly_detector.py` with new detection algorithms.

---

## Performance

- **Memory Usage**: ~50-100 MB (depends on historical data size)
- **CPU Usage**: <5% (idle), <20% (active monitoring)
- **Network**: Minimal (queries every 30s by default)

---

## Security

- Never commit `.env` files with real credentials
- Use Kubernetes secrets for production
- Enable TLS for RabbitMQ in production
- Restrict Prometheus access with authentication

---

## License

See LICENSE file in project root.

---

## Support

For issues and questions, refer to the main devops project documentation.
