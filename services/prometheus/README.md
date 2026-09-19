# Prometheus Service for Azure Container Apps

This is a simplified Prometheus deployment configured for Azure Container Apps environment.

## Overview

Prometheus is deployed as a Container App to scrape metrics from test-app and provide query API for monitoring-agent.

## Configuration

- **Config File**: `prometheus-azure.yml`
- **Scrape Targets**:
  - Prometheus itself (localhost:9090)
  - test-app (test-app:8080/metrics)
- **Scrape Interval**: 10 seconds
- **Platform**: Azure Container Apps (no Kubernetes service discovery)

## Dockerfile

Uses official Prometheus v2.48.0 image with custom Azure configuration.

## Deployment

Deploy to Azure Container Apps:

```bash
az containerapp create \
  --name prometheus \
  --resource-group devops-india-rg \
  --environment devops-ai-env \
  --image nidhi-upadhye03/prometheus:latest \
  --target-port 9090 \
  --ingress internal \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 1
```

## Access

- Internal URL: `http://prometheus:9090`
- Used by: monitoring-agent to query metrics
- Web UI: Available at `http://prometheus:9090` (internal only)

## Metrics Scraped

From test-app:
- CPU usage
- Memory usage
- HTTP request metrics
- Error rates
- Custom chaos metrics

## Notes

- No persistent storage (metrics stored in-memory only)
- Metrics retained for 30 days (default)
- Suitable for development/testing environments
- For production, consider Azure Monitor or persistent storage

