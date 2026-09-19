# Monitoring Stack Setup Guide

This directory contains a complete production-ready monitoring stack for Kubernetes, including Prometheus, Grafana, ELK (Elasticsearch, Logstash, Kibana), and Alertmanager.

## Architecture Overview

### Components

1. **Prometheus** - Metrics collection and storage
2. **Grafana** - Metrics visualization and dashboards
3. **Elasticsearch** - Log storage and indexing
4. **Logstash** - Log processing and transformation
5. **Kibana** - Log visualization and analysis
6. **Filebeat** - Log collection from pods
7. **Alertmanager** - Alert routing and notification

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured to access your cluster
- StorageClass named "standard" available (or modify the manifests)
- Sufficient cluster resources:
  - At least 3 nodes with 8GB RAM each
  - 200GB+ available storage

## Quick Start

### 1. Create Monitoring Namespace

```bash
kubectl create namespace monitoring
```

### 2. Deploy Prometheus

```bash
# Deploy Prometheus with configuration
kubectl apply -f prometheus/prometheus-configmap.yaml
kubectl apply -f prometheus/prometheus-rules.yaml
kubectl apply -f prometheus/prometheus-deployment.yaml
kubectl apply -f prometheus/prometheus-service.yaml

# Optional: Deploy ServiceMonitors (requires Prometheus Operator)
kubectl apply -f prometheus/servicemonitor.yaml
```

### 3. Deploy Grafana

```bash
# Deploy Grafana
kubectl apply -f grafana/grafana-configmap.yaml
kubectl apply -f grafana/grafana-datasources-configmap.yaml
kubectl apply -f grafana/grafana-dashboards-configmap.yaml
kubectl apply -f grafana/grafana-deployment.yaml
kubectl apply -f grafana/grafana-service.yaml
```

### 4. Deploy ELK Stack

```bash
# Deploy Elasticsearch cluster
kubectl apply -f elk/elasticsearch-statefulset.yaml
kubectl apply -f elk/elasticsearch-service.yaml

# Wait for Elasticsearch to be ready
kubectl wait --for=condition=ready pod -l app=elasticsearch -n monitoring --timeout=300s

# Deploy Logstash
kubectl apply -f elk/logstash-configmap.yaml
kubectl apply -f elk/logstash-deployment.yaml

# Deploy Kibana
kubectl apply -f elk/kibana-deployment.yaml
kubectl apply -f elk/kibana-service.yaml

# Deploy Filebeat (log collection)
kubectl apply -f elk/filebeat-daemonset.yaml
```

### 5. Deploy Alertmanager

```bash
# Configure Alertmanager (update with your SMTP, Slack, PagerDuty credentials first!)
kubectl apply -f alertmanager/alertmanager-configmap.yaml
kubectl apply -f alertmanager/alertmanager-deployment.yaml
kubectl apply -f alertmanager/alertmanager-service.yaml
```

## Accessing the Services

### Using NodePort (Development)

The services are exposed via NodePort for easy access:

- **Prometheus**: http://NODE_IP:30090
- **Grafana**: http://NODE_IP:30300
- **Kibana**: http://NODE_IP:30561
- **Alertmanager**: http://NODE_IP:30093
- **Elasticsearch**: http://NODE_IP:30920

Replace NODE_IP with your Kubernetes node's IP address.

### Using Port Forwarding

```bash
# Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Kibana
kubectl port-forward -n monitoring svc/kibana 5601:5601

# Alertmanager
kubectl port-forward -n monitoring svc/alertmanager 9093:9093
```

### Production Ingress (Recommended)

For production, configure Ingress resources:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring-ingress
  namespace: monitoring
spec:
  rules:
  - host: prometheus.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus
            port:
              number: 9090
  - host: grafana.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
  - host: kibana.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kibana
            port:
              number: 5601
```

## Default Credentials

### Grafana
- **Username**: admin
- **Password**: changeme123! (Change this immediately!)

Update the password in `grafana/grafana-deployment.yaml` before deploying.

## Grafana Dashboards

Four pre-configured dashboards are included:

1. **LLM Service Dashboard** - LLM metrics, token usage, latency
2. **Worker Service Dashboard** - Queue depth, task processing, failures
3. **System Overview Dashboard** - Overall system health and metrics
4. **Approval Dashboard** - Approval workflow metrics

Access them in Grafana after deployment.

## Alertmanager Configuration

Before deploying Alertmanager, update `alertmanager/alertmanager-configmap.yaml` with your credentials:

1. **Email Configuration**
   ```yaml
   smtp_smarthost: 'smtp.gmail.com:587'
   smtp_from: 'alerts@company.com'
   smtp_auth_username: 'alerts@company.com'
   smtp_auth_password: 'your-smtp-password'
   ```

2. **Slack Configuration**
   ```yaml
   slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
   ```

3. **PagerDuty Configuration**
   ```yaml
   pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'
   # Update service keys in receiver configurations
   ```

## Prometheus Scrape Configuration

Ensure your services expose metrics on the expected ports and paths:

- **LLM Service**: Port 8080, path `/metrics`
- **Worker Service**: Port 8080, path `/metrics`
- **API Gateway**: Port 8080, path `/metrics`
- **Approval Service**: Port 8080, path `/metrics`

Add Prometheus annotations to your service pods:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
```

## Alert Rules

Comprehensive alert rules are configured in `prometheus/prometheus-rules.yaml`:

- **Service Alerts**: High error rates, service downtime, latency issues
- **Resource Alerts**: CPU, memory, disk usage warnings
- **Database Alerts**: PostgreSQL, Redis, RabbitMQ issues
- **Kubernetes Alerts**: Node status, pod issues, PVC problems

See `ALERTS.md` for detailed alert definitions and runbooks.

## Log Collection

Filebeat automatically collects logs from all pods in the cluster. Logs are:

1. Collected by Filebeat (DaemonSet on each node)
2. Sent to Logstash for processing
3. Transformed and enriched with Kubernetes metadata
4. Stored in Elasticsearch
5. Visualized in Kibana

### Viewing Logs in Kibana

1. Access Kibana UI
2. Go to "Management" > "Stack Management" > "Index Patterns"
3. Create index pattern: `logstash-*`
4. Set time field: `@timestamp`
5. Go to "Discover" to view logs

## Resource Requirements

### Minimum Resources

| Component | Replicas | CPU Request | Memory Request | Storage |
|-----------|----------|-------------|----------------|---------|
| Prometheus | 1 | 500m | 2Gi | 50Gi |
| Grafana | 1 | 250m | 512Mi | 10Gi |
| Elasticsearch | 3 | 1000m | 3Gi | 100Gi each |
| Logstash | 2 | 500m | 1.5Gi | - |
| Kibana | 1 | 500m | 1Gi | 10Gi |
| Filebeat | DaemonSet | 100m | 200Mi | - |
| Alertmanager | 1 | 100m | 128Mi | 5Gi |

### Production Recommendations

- Use dedicated storage class with good IOPS for Elasticsearch
- Enable Prometheus remote write for long-term storage
- Configure backup for Grafana dashboards
- Set up Elasticsearch snapshots for disaster recovery
- Use persistent volumes for all stateful components

## Troubleshooting

### Prometheus Not Scraping Targets

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Visit http://localhost:9090/targets

# Check ServiceAccount permissions
kubectl get clusterrolebinding prometheus -o yaml

# Verify pod annotations
kubectl get pod <pod-name> -o yaml | grep prometheus.io
```

### Elasticsearch Pods Not Starting

```bash
# Check pod status
kubectl get pods -n monitoring -l app=elasticsearch

# Check logs
kubectl logs -n monitoring elasticsearch-0

# Common issues:
# - Insufficient memory (increase node memory)
# - vm.max_map_count too low (set on host: sysctl -w vm.max_map_count=262144)
# - PVC not bound (check storage class)
```

### Filebeat Not Collecting Logs

```bash
# Check Filebeat pods
kubectl get pods -n monitoring -l app=filebeat

# Check logs
kubectl logs -n monitoring -l app=filebeat

# Verify Logstash is accepting connections
kubectl port-forward -n monitoring svc/logstash 5044:5044
```

### Grafana Dashboards Not Loading

```bash
# Check Grafana logs
kubectl logs -n monitoring deployment/grafana

# Verify datasource connection
# In Grafana UI: Configuration > Data Sources > Prometheus > Test

# Check ConfigMap
kubectl get configmap -n monitoring grafana-datasources -o yaml
```

### Alerts Not Firing

```bash
# Check Prometheus rules
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Visit http://localhost:9090/rules

# Check Alertmanager
kubectl port-forward -n monitoring svc/alertmanager 9093:9093
# Visit http://localhost:9093

# Verify Alertmanager configuration
kubectl logs -n monitoring deployment/alertmanager
```

## Maintenance

### Scaling

```bash
# Scale Elasticsearch
kubectl scale statefulset -n monitoring elasticsearch --replicas=5

# Scale Logstash
kubectl scale deployment -n monitoring logstash --replicas=3
```

### Backup

```bash
# Backup Grafana dashboards
kubectl exec -n monitoring deployment/grafana -- grafana-cli admin export-dashboard

# Backup Prometheus data (use remote write or snapshots)
# Configure in prometheus.yml:
# remote_write:
#   - url: "https://your-long-term-storage/api/v1/write"

# Backup Elasticsearch
# Use Elasticsearch snapshot API
```

### Updating

```bash
# Update image versions in deployment files
# Then apply changes
kubectl apply -f <updated-file>.yaml

# For StatefulSets, use rolling update
kubectl rollout status statefulset -n monitoring elasticsearch
```

## Security Considerations

1. **Enable Authentication**
   - Grafana: Already configured with admin user
   - Prometheus: Add HTTP basic auth via nginx-ingress
   - Kibana: Enable X-Pack security in Elasticsearch
   - Alertmanager: Add HTTP basic auth

2. **Network Policies**
   - Restrict pod-to-pod communication
   - Only allow necessary ingress/egress

3. **Secrets Management**
   - Store credentials in Kubernetes Secrets, not ConfigMaps
   - Use external secret managers (Vault, AWS Secrets Manager)

4. **TLS/SSL**
   - Enable TLS for all external communications
   - Use cert-manager for certificate management

5. **RBAC**
   - Limit ServiceAccount permissions
   - Use least privilege principle

## Integration with Applications

### Adding Metrics to Your Services

1. **Expose Metrics Endpoint**
   ```javascript
   // Example: Node.js with prom-client
   const promClient = require('prom-client');
   const register = promClient.register;

   app.get('/metrics', (req, res) => {
     res.set('Content-Type', register.contentType);
     res.end(register.metrics());
   });
   ```

2. **Add Prometheus Annotations**
   ```yaml
   metadata:
     annotations:
       prometheus.io/scrape: "true"
       prometheus.io/port: "8080"
   ```

### Structured Logging

For best Kibana integration, use structured JSON logging:

```javascript
// Example: Winston logger
const logger = winston.createLogger({
  format: winston.format.json(),
  defaultMeta: {
    service: 'llm-service',
    version: '1.0.0'
  },
  transports: [
    new winston.transports.Console()
  ]
});

logger.info('Request processed', {
  request_id: 'abc123',
  user_id: 'user456',
  http: {
    method: 'POST',
    path: '/api/generate',
    status: 200,
    duration_ms: 1234
  }
});
```

## Support

For issues or questions:
- Check the troubleshooting section
- Review component logs
- Consult official documentation:
  - [Prometheus](https://prometheus.io/docs/)
  - [Grafana](https://grafana.com/docs/)
  - [Elasticsearch](https://www.elastic.co/guide/)
  - [Alertmanager](https://prometheus.io/docs/alerting/alertmanager/)

## License

This monitoring stack configuration is provided as-is for use with your applications.
