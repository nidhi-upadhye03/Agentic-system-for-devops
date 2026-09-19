# Test Application - Chaos Engineering

A simple Python Flask application designed to generate controllable errors for testing the **LLM DevOps Copilot**. This app deliberately triggers various failure scenarios (CPU spikes, memory leaks, crashes, HTTP errors) so that the autonomous agents can detect and remediate them.

## Purpose

This test app validates the end-to-end functionality of the LLM DevOps Copilot:

1. **Monitoring Agent** detects anomalies via Prometheus metrics
2. **Analyzer Agent** performs LLM-powered root cause analysis
3. **Auto-Response Agent** executes remediation actions (scale/restart/rollback)
4. **Notifier Agent** sends Slack notifications
5. **Memory Agent** learns from incident patterns

## Features

- **Prometheus Metrics**: Exposes `/metrics` endpoint for monitoring
- **Controllable Chaos**: Trigger errors via REST API
- **Multiple Failure Modes**: CPU, memory, crashes, HTTP errors
- **Background Metrics**: Continuously updates system metrics
- **Reset Capability**: Stop all chaos scenarios

## Endpoints

### Health & Status

- `GET /` - Root endpoint showing all available chaos endpoints
- `GET /health` - Health check (returns 500 with 30% probability when error mode active)
- `GET /status` - Current chaos state and system metrics
- `GET /metrics` - Prometheus metrics endpoint

### Chaos Triggers

#### High CPU Usage
```bash
POST /trigger-cpu
```
Causes 80%+ CPU usage for 2 minutes via busy loop.

**Expected Behavior:**
- CPU usage spikes above 80%
- Monitoring Agent detects anomaly
- Analyzer Agent identifies CPU bottleneck
- Auto-Response Agent may scale or restart pod

#### Memory Leak
```bash
POST /trigger-memory
```
Allocates 50MB of memory every 10 seconds until stopped.

**Expected Behavior:**
- Memory usage increases continuously
- Monitoring Agent detects memory growth
- Analyzer Agent identifies memory leak
- Auto-Response Agent restarts pod to free memory

#### Application Crash
```bash
POST /trigger-crash
```
Crashes the application after 2 seconds (forces pod restart).

**Expected Behavior:**
- Application terminates with exit code 1
- Container orchestrator restarts pod
- Monitoring Agent detects pod restart
- Analyzer Agent identifies crash pattern

#### HTTP 500 Errors
```bash
POST /trigger-errors
```
Enables 50% HTTP 500 error rate on all endpoints.

**Expected Behavior:**
- Health check fails 30% of the time
- Error rate increases dramatically
- Monitoring Agent detects error spike
- Analyzer Agent analyzes error patterns

#### Stop All Chaos
```bash
POST /reset
```
Stops all active chaos scenarios and frees allocated memory.

## Testing Workflow

### 1. Deploy the Application

The test app is automatically deployed to Azure Container Apps via the `deploy-from-dockerhub.sh` script.

### 2. Trigger Chaos Scenarios

From Azure Cloud Shell or any machine with network access to the internal Azure Container Apps environment:

```bash
# Get the test-app FQDN
TEST_APP_URL="http://test-app.internal.example.azurecontainerapps.io"

# Trigger high CPU usage
curl -X POST $TEST_APP_URL/trigger-cpu

# Wait 30-60 seconds for monitoring agent to detect
# Check Slack for notifications

# Stop chaos
curl -X POST $TEST_APP_URL/reset

# Trigger memory leak
curl -X POST $TEST_APP_URL/trigger-memory

# Monitor memory growth
curl $TEST_APP_URL/status

# Stop chaos
curl -X POST $TEST_APP_URL/reset
```

### 3. Monitor Agent Response

Watch the following:

1. **Slack Notifications**: Notifier Agent sends alerts
2. **Azure Container Apps Logs**: View agent responses
   ```bash
   az containerapp logs show --name monitoring-agent --resource-group devops-india-rg --follow
   az containerapp logs show --name analyzer-agent --resource-group devops-india-rg --follow
   az containerapp logs show --name auto-response-agent --resource-group devops-india-rg --follow
   ```
3. **Prometheus Metrics**: Check metrics endpoint
   ```bash
   curl $TEST_APP_URL/metrics
   ```

## Prometheus Metrics Exposed

```
test_app_requests_total{endpoint="/health", status="200"}
test_app_requests_total{endpoint="/health", status="500"}
test_app_errors_total
test_app_cpu_percent
test_app_memory_mb
test_app_chaos_active{type="cpu"}
test_app_chaos_active{type="memory"}
test_app_chaos_active{type="errors"}
```

## Configuration

Environment variables (optional):

- `PORT` - HTTP port (default: 8080)

## Local Development

### Run with Docker

```bash
cd services/test-app
docker build -t test-app .
docker run -p 8080:8080 test-app
```

### Run Locally (Python)

```bash
cd services/test-app
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

Access the app at `http://localhost:8080`

## Expected Agent Behavior

### CPU Spike Scenario

1. Monitoring Agent detects `test_app_cpu_percent > 80`
2. Publishes `monitoring.incident.cpu_high` to RabbitMQ
3. Analyzer Agent analyzes metrics and logs
4. Determines root cause: "High CPU usage due to compute-intensive operation"
5. Recommends: "Scale horizontally or restart pod"
6. Auto-Response Agent executes remediation
7. Notifier Agent sends Slack notification
8. Memory Agent stores incident pattern

### Memory Leak Scenario

1. Monitoring Agent detects increasing `test_app_memory_mb`
2. Publishes `monitoring.incident.memory_leak` to RabbitMQ
3. Analyzer Agent analyzes memory growth rate
4. Determines root cause: "Memory leak - continuous allocation without release"
5. Recommends: "Restart pod to free memory"
6. Auto-Response Agent restarts pod
7. Notifier Agent sends Slack notification
8. Memory Agent learns from pattern

### Crash Loop Scenario

1. Monitoring Agent detects pod restarts
2. Publishes `monitoring.incident.crash_loop` to RabbitMQ
3. Analyzer Agent analyzes crash logs
4. Determines root cause: "Application crash - exit code 1"
5. Recommends: "Investigate application logs, rollback if recent deploy"
6. Auto-Response Agent may rollback or scale down
7. Notifier Agent sends critical alert
8. Memory Agent stores incident for future reference

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚          Test App                   â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”‚
â”‚  â”‚   Flask Web Server         â”‚    â”‚
â”‚  â”‚   - Chaos endpoints        â”‚    â”‚
â”‚  â”‚   - Health check           â”‚    â”‚
â”‚  â”‚   - Prometheus metrics     â”‚    â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â”‚                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”‚
â”‚  â”‚   Background Threads       â”‚    â”‚
â”‚  â”‚   - CPU burn worker        â”‚    â”‚
â”‚  â”‚   - Memory leak worker     â”‚    â”‚
â”‚  â”‚   - Metrics updater        â”‚    â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              â”‚ Exposes Metrics
              â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚      Monitoring Agent               â”‚
â”‚  - Scrapes /metrics endpoint        â”‚
â”‚  - Detects anomalies                â”‚
â”‚  - Publishes incidents to RabbitMQ  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Troubleshooting

### Test App Not Responding

```bash
# Check if pod is running
az containerapp show --name test-app --resource-group devops-india-rg

# Check logs
az containerapp logs show --name test-app --resource-group devops-india-rg --follow
```

### Metrics Not Updating

The metrics updater thread runs every 5 seconds. If metrics are stale:
- Check if the app crashed
- Restart the pod: `curl -X POST $TEST_APP_URL/trigger-crash` (will auto-restart)

### Chaos Not Stopping

Use the reset endpoint:
```bash
curl -X POST $TEST_APP_URL/reset
```

If that doesn't work, restart the pod manually:
```bash
az containerapp revision restart --name test-app --resource-group devops-india-rg
```

## Docker Hub

Pre-built image: `nidhi-upadhye03/test-app:latest`

Built automatically via GitHub Actions on every push to `main` branch.

## License

MIT License - Part of the LLM DevOps Copilot

