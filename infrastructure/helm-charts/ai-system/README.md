# AI System Helm Chart

A comprehensive Helm chart for deploying the AI System with LLM Service, Worker, Approval Backend, Approval Frontend, and supporting infrastructure (PostgreSQL, Redis, RabbitMQ).

## Features

- Microservices architecture with 4 main services
- Full infrastructure stack (PostgreSQL, Redis, RabbitMQ)
- Environment-specific configurations (dev, staging, prod)
- Horizontal Pod Autoscaling (HPA)
- Network policies for security
- RBAC support
- Ingress configuration with TLS
- Persistent storage for databases
- Health checks and probes
- Resource limits and requests

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (for persistence)
- Ingress controller (nginx recommended)
- cert-manager (optional, for TLS certificates)

## Components

### Application Services

1. **LLM Service** - AI/ML service for language model processing
2. **Worker** - Background task processing with Celery
3. **Approval Backend** - Node.js REST API backend
4. **Approval Frontend** - React frontend application

### Infrastructure Services

1. **PostgreSQL** - Primary database
2. **Redis** - Cache and session storage
3. **RabbitMQ** - Message queue for worker tasks

## Installation

### Quick Start (Development)

```bash
# Install with default dev values
helm install ai-system ./ai-system

# Or with explicit dev values
helm install ai-system ./ai-system -f ./ai-system/values-dev.yaml
```

### Staging Environment

```bash
helm install ai-system ./ai-system \
  -f ./ai-system/values-staging.yaml \
  --namespace ai-system-staging \
  --create-namespace
```

### Production Environment

```bash
# Create secrets first (using external secrets operator or manually)
kubectl create secret generic ai-system-secrets \
  --from-literal=DATABASE_URL="postgresql://..." \
  --from-literal=REDIS_URL="redis://..." \
  --from-literal=RABBITMQ_URL="amqp://..." \
  --from-literal=JWT_SECRET="..." \
  --from-literal=OPENAI_API_KEY="..." \
  -n ai-system-prod

# Install chart
helm install ai-system ./ai-system \
  -f ./ai-system/values-prod.yaml \
  --namespace ai-system-prod \
  --create-namespace
```

## Configuration

### Values Files

- `values.yaml` - Default values (dev-like settings)
- `values-dev.yaml` - Development environment
- `values-staging.yaml` - Staging environment
- `values-prod.yaml` - Production environment

### Key Configuration Parameters

#### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `dev` |
| `global.namespace` | Kubernetes namespace | `ai-system-dev` |
| `global.domain` | Domain name | `dev.ai-system.local` |
| `global.imagePullPolicy` | Image pull policy | `IfNotPresent` |

#### LLM Service

| Parameter | Description | Default |
|-----------|-------------|---------|
| `llmService.enabled` | Enable LLM service | `true` |
| `llmService.replicaCount` | Number of replicas | `1` |
| `llmService.image.repository` | Image repository | `your-registry/llm-service` |
| `llmService.image.tag` | Image tag | `latest` |
| `llmService.resources.requests.cpu` | CPU request | `500m` |
| `llmService.resources.requests.memory` | Memory request | `1Gi` |
| `llmService.autoscaling.enabled` | Enable HPA | `false` |

#### Worker

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker | `true` |
| `worker.replicaCount` | Number of replicas | `2` |
| `worker.env.WORKER_CONCURRENCY` | Celery concurrency | `4` |

#### Approval Backend

| Parameter | Description | Default |
|-----------|-------------|---------|
| `approvalBackend.enabled` | Enable backend | `true` |
| `approvalBackend.replicaCount` | Number of replicas | `1` |
| `approvalBackend.env.NODE_ENV` | Node environment | `development` |

#### Approval Frontend

| Parameter | Description | Default |
|-----------|-------------|---------|
| `approvalFrontend.enabled` | Enable frontend | `true` |
| `approvalFrontend.replicaCount` | Number of replicas | `1` |

#### PostgreSQL

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.database` | Database name | `ai_system` |
| `postgresql.auth.username` | Database user | `postgres` |
| `postgresql.persistence.enabled` | Enable persistence | `true` |
| `postgresql.persistence.size` | Storage size | `10Gi` |

#### Redis

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.auth.enabled` | Enable authentication | `true` |
| `redis.persistence.enabled` | Enable persistence | `true` |
| `redis.persistence.size` | Storage size | `5Gi` |

#### RabbitMQ

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rabbitmq.enabled` | Enable RabbitMQ | `true` |
| `rabbitmq.auth.username` | Admin username | `admin` |
| `rabbitmq.persistence.enabled` | Enable persistence | `true` |
| `rabbitmq.persistence.size` | Storage size | `8Gi` |

#### Ingress

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | Hostname | `dev.ai-system.local` |

## Upgrading

```bash
# Upgrade with new values
helm upgrade ai-system ./ai-system -f ./ai-system/values-prod.yaml

# Upgrade with specific values
helm upgrade ai-system ./ai-system \
  --set llmService.replicaCount=3 \
  --set worker.replicaCount=5
```

## Uninstalling

```bash
# Uninstall release
helm uninstall ai-system

# Uninstall and delete namespace
helm uninstall ai-system
kubectl delete namespace ai-system-dev
```

## Monitoring

### Check Pod Status

```bash
kubectl get pods -n ai-system-dev
```

### View Logs

```bash
# LLM Service
kubectl logs -n ai-system-dev -l app.kubernetes.io/component=llm-service -f

# Worker
kubectl logs -n ai-system-dev -l app.kubernetes.io/component=worker -f

# Backend
kubectl logs -n ai-system-dev -l app.kubernetes.io/component=approval-backend -f

# Frontend
kubectl logs -n ai-system-dev -l app.kubernetes.io/component=approval-frontend -f
```

### Access RabbitMQ Management

```bash
kubectl port-forward -n ai-system-dev svc/ai-system-rabbitmq 15672:15672
# Open http://localhost:15672
```

### Access Services Locally

```bash
# Frontend
kubectl port-forward -n ai-system-dev svc/ai-system-approval-frontend 8080:80

# Backend API
kubectl port-forward -n ai-system-dev svc/ai-system-approval-backend 3000:3000

# LLM Service
kubectl port-forward -n ai-system-dev svc/ai-system-llm-service 8000:8000
```

## Security

### Secrets Management

For production, use one of these approaches:

1. **External Secrets Operator** (Recommended)
```yaml
# Install external-secrets-operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

2. **Sealed Secrets**
```bash
# Install sealed-secrets controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system
```

3. **HashiCorp Vault**

### Network Policies

Network policies are enabled by default in staging and production:

```yaml
networkPolicy:
  enabled: true
```

This restricts pod-to-pod communication to only necessary paths.

### RBAC

RBAC is enabled by default with minimal permissions:

```yaml
rbac:
  enabled: true
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n ai-system-dev

# Check logs
kubectl logs <pod-name> -n ai-system-dev
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
kubectl get pods -n ai-system-dev -l app.kubernetes.io/component=postgresql

# Test connection
kubectl exec -it -n ai-system-dev <postgres-pod> -- psql -U postgres -d ai_system
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n ai-system-dev

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

## Development

### Template Validation

```bash
# Dry run to validate templates
helm install ai-system ./ai-system --dry-run --debug

# Template rendering
helm template ai-system ./ai-system -f ./ai-system/values-dev.yaml
```

### Linting

```bash
# Lint chart
helm lint ./ai-system
```

## Contributing

1. Make changes to the chart
2. Update version in Chart.yaml
3. Test with `helm lint` and `helm install --dry-run`
4. Update this README if needed
5. Submit pull request

## License

Copyright (c) 2024 Your Organization

## Support

- Documentation: https://docs.ai-system.com
- GitHub: https://github.com/your-org/ai-system
- Email: support@ai-system.com
