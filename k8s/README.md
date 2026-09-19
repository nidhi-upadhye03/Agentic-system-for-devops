# Kubernetes Manifests for AI System

This directory contains complete Kubernetes manifests for deploying the AI system with all its components.

## Directory Structure

```
k8s/
├── base/                           # Base Kubernetes manifests
│   ├── namespace.yaml              # ai-system namespace
│   ├── rbac.yaml                   # RBAC roles and bindings
│   ├── configmap.yaml              # Common configuration
│   ├── secrets.yaml                # Secret references
│   ├── llm-service-deployment.yaml # LLM service (3 replicas)
│   ├── llm-service-service.yaml    # LLM ClusterIP service
│   ├── worker-service-deployment.yaml  # Worker deployment
│   ├── worker-service-service.yaml     # Worker service
│   ├── approval-backend-deployment.yaml    # Backend API
│   ├── approval-backend-service.yaml       # Backend service
│   ├── approval-frontend-deployment.yaml   # Frontend with NGINX
│   ├── approval-frontend-service.yaml      # Frontend service
│   ├── rabbitmq-statefulset.yaml  # RabbitMQ cluster (3 replicas)
│   ├── rabbitmq-service.yaml       # RabbitMQ services
│   ├── postgres-statefulset.yaml   # PostgreSQL with PVC
│   ├── postgres-service.yaml       # PostgreSQL service
│   ├── redis-deployment.yaml       # Redis with persistence
│   ├── redis-service.yaml          # Redis service
│   ├── ingress.yaml                # Ingress with TLS
│   ├── hpa.yaml                    # Horizontal Pod Autoscalers
│   ├── networkpolicy.yaml          # Network security policies
│   └── kustomization.yaml          # Base kustomization
│
└── overlays/                       # Environment-specific overlays
    ├── dev/
    │   ├── kustomization.yaml      # Dev configuration
    │   ├── configmap-patch.yaml    # Dev config overrides
    │   ├── replica-patch.yaml      # 1 replica, lower resources
    │   └── namespace-patch.yaml    # Dev namespace labels
    │
    ├── staging/
    │   ├── kustomization.yaml      # Staging configuration
    │   ├── configmap-patch.yaml    # Staging config overrides
    │   ├── replica-patch.yaml      # 2 replicas, medium resources
    │   └── namespace-patch.yaml    # Staging namespace labels
    │
    └── prod/
        ├── kustomization.yaml      # Production configuration
        ├── configmap-patch.yaml    # Production config overrides
        ├── replica-patch.yaml      # 5+ replicas, high resources
        ├── ingress-patch.yaml      # Production domains and TLS
        └── namespace-patch.yaml    # Production namespace labels
```

## Components

### Application Services
- **LLM Service**: AI/ML language model service (3-5 replicas)
- **Worker Service**: Background job processor (3-5 replicas)
- **Approval Backend**: REST API backend (3-5 replicas)
- **Approval Frontend**: NGINX-served React app (2-3 replicas)

### Infrastructure
- **PostgreSQL**: Primary database with persistent storage
- **Redis**: Cache and session store with persistence
- **RabbitMQ**: Message queue cluster (3 replicas)

### Features
- **Horizontal Pod Autoscaling**: Automatic scaling based on CPU/memory
- **Network Policies**: Zero-trust network security
- **RBAC**: Role-based access control
- **Ingress**: TLS-enabled external access
- **Health Checks**: Liveness, readiness, and startup probes
- **Resource Limits**: CPU and memory constraints
- **Security Contexts**: Non-root users, read-only filesystems

## Prerequisites

1. **Kubernetes Cluster**: v1.24+
2. **kubectl**: Kubernetes CLI tool
3. **kustomize**: Built into kubectl v1.14+
4. **Ingress Controller**: NGINX Ingress Controller
5. **cert-manager**: For TLS certificate management
6. **Storage Class**: For persistent volumes

## Deployment

### Development Environment

```bash
# Apply dev configuration
kubectl apply -k overlays/dev/

# Verify deployment
kubectl get all -n ai-system

# Check pods
kubectl get pods -n ai-system -w
```

### Staging Environment

```bash
# Apply staging configuration
kubectl apply -k overlays/staging/

# Verify deployment
kubectl get all -n ai-system
```

### Production Environment

```bash
# Apply production configuration
kubectl apply -k overlays/prod/

# Verify deployment
kubectl get all -n ai-system

# Check ingress
kubectl get ingress -n ai-system
```

## Configuration

### Environment Variables

All environment-specific configuration is in the overlays:
- `overlays/dev/configmap-patch.yaml` - Development settings
- `overlays/staging/configmap-patch.yaml` - Staging settings
- `overlays/prod/configmap-patch.yaml` - Production settings

### Secrets Management

**Important**: Update secrets before deploying to production!

The base `secrets.yaml` contains placeholder values. For production:

1. **Option 1: Sealed Secrets**
```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Seal your secrets
kubeseal --format yaml < secrets.yaml > sealed-secrets.yaml
```

2. **Option 2: External Secrets Operator**
```bash
# Install external-secrets operator
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Configure secret store (AWS Secrets Manager, Azure Key Vault, etc.)
```

3. **Option 3: Manual Secret Creation**
```bash
kubectl create secret generic ai-system-secrets \
  --from-literal=POSTGRES_PASSWORD=your-secure-password \
  --from-literal=REDIS_PASSWORD=your-redis-password \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  -n ai-system
```

### Container Images

Update image registry and tags in:
- `base/kustomization.yaml` - Base images
- `overlays/*/kustomization.yaml` - Environment-specific tags

```yaml
images:
  - name: llm-service
    newName: your-registry.azurecr.io/llm-service
    newTag: v1.0.0
```

### Domain Names

Update domains in `overlays/prod/ingress-patch.yaml`:
```yaml
hosts:
  - ai-system.example.com        # Frontend
  - api.ai-system.example.com    # Backend API
```

## Resource Allocation

### Development
- LLM Service: 1 replica, 1Gi memory, 500m CPU
- Worker: 1 replica, 256Mi memory, 250m CPU
- Backend: 1 replica, 128Mi memory, 100m CPU
- Frontend: 1 replica, 64Mi memory, 50m CPU

### Staging
- LLM Service: 2 replicas, 1.5Gi memory, 750m CPU
- Worker: 2 replicas, 384Mi memory, 350m CPU
- Backend: 2 replicas, 192Mi memory, 200m CPU
- Frontend: 2 replicas, 96Mi memory, 75m CPU

### Production
- LLM Service: 5 replicas (auto-scales to 20), 3Gi memory, 1.5 CPU
- Worker: 5 replicas (auto-scales to 30), 768Mi memory, 750m CPU
- Backend: 5 replicas (auto-scales to 15), 512Mi memory, 500m CPU
- Frontend: 3 replicas (auto-scales to 12), 192Mi memory, 150m CPU

## Monitoring

### Check Pod Status
```bash
kubectl get pods -n ai-system
kubectl describe pod <pod-name> -n ai-system
kubectl logs <pod-name> -n ai-system -f
```

### Check Services
```bash
kubectl get svc -n ai-system
kubectl get ingress -n ai-system
```

### Check HPA
```bash
kubectl get hpa -n ai-system
kubectl describe hpa llm-service-hpa -n ai-system
```

### Check Network Policies
```bash
kubectl get networkpolicies -n ai-system
kubectl describe networkpolicy <policy-name> -n ai-system
```

## Troubleshooting

### Pods Not Starting
```bash
kubectl describe pod <pod-name> -n ai-system
kubectl logs <pod-name> -n ai-system
```

### Service Not Reachable
```bash
kubectl get endpoints -n ai-system
kubectl describe service <service-name> -n ai-system
```

### Ingress Issues
```bash
kubectl describe ingress ai-system-ingress -n ai-system
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### Database Connection Issues
```bash
# Check PostgreSQL
kubectl exec -it postgres-0 -n ai-system -- psql -U ai_user -d ai_system

# Check Redis
kubectl exec -it <redis-pod> -n ai-system -- redis-cli ping

# Check RabbitMQ
kubectl exec -it rabbitmq-0 -n ai-system -- rabbitmq-diagnostics status
```

## Backup and Recovery

### PostgreSQL Backup
```bash
kubectl exec postgres-0 -n ai-system -- pg_dump -U ai_user ai_system > backup.sql
```

### PostgreSQL Restore
```bash
kubectl cp backup.sql ai-system/postgres-0:/tmp/backup.sql
kubectl exec postgres-0 -n ai-system -- psql -U ai_user -d ai_system -f /tmp/backup.sql
```

### Redis Backup
```bash
kubectl exec <redis-pod> -n ai-system -- redis-cli BGSAVE
kubectl cp ai-system/<redis-pod>:/data/dump.rdb ./redis-backup.rdb
```

## Scaling

### Manual Scaling
```bash
# Scale LLM service
kubectl scale deployment llm-service -n ai-system --replicas=5

# Scale workers
kubectl scale deployment worker-service -n ai-system --replicas=10
```

### Auto-scaling Configuration
Edit HPA resources in `base/hpa.yaml` or create patches in overlays.

## Security

### Network Policies
- Default deny all traffic
- Explicit allow rules for required connections
- Frontend can only access backend
- Backend can access databases
- Workers can access RabbitMQ, Redis, PostgreSQL, and LLM service

### RBAC
- Service accounts with minimal permissions
- Pod security policies enabled
- Read-only root filesystems
- Non-root users
- Dropped capabilities

### TLS/SSL
- Ingress configured with TLS
- cert-manager for automatic certificate management
- Force SSL redirect enabled

## Maintenance

### Update Deployment
```bash
# Update image tag
kubectl set image deployment/llm-service llm-service=new-image:tag -n ai-system

# Or apply updated kustomization
kubectl apply -k overlays/prod/
```

### Rollback
```bash
kubectl rollout undo deployment/llm-service -n ai-system
kubectl rollout status deployment/llm-service -n ai-system
```

### Clean Up
```bash
# Delete specific environment
kubectl delete -k overlays/dev/

# Delete entire namespace (careful!)
kubectl delete namespace ai-system
```

## Best Practices

1. **Always test in dev/staging** before deploying to production
2. **Use sealed secrets or external secrets** for sensitive data
3. **Monitor resource usage** and adjust limits accordingly
4. **Set up alerts** for pod failures, high resource usage
5. **Regular backups** of PostgreSQL and Redis data
6. **Use specific image tags** instead of `latest` in production
7. **Review logs regularly** for errors and warnings
8. **Test disaster recovery** procedures periodically
9. **Keep Kubernetes and dependencies updated**
10. **Document all changes** to manifests

## Support

For issues or questions:
- Check logs: `kubectl logs <pod-name> -n ai-system`
- Review events: `kubectl get events -n ai-system --sort-by='.lastTimestamp'`
- Contact: devops@example.com
