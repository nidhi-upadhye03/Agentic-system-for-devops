# CI/CD Pipeline Documentation

Complete GitHub Actions CI/CD pipeline for containerized Node.js applications with Kubernetes deployment.

## Overview

This directory contains a comprehensive CI/CD pipeline setup including:
- **6 GitHub Actions workflows** for automated build, test, security, and deployment
- **5 Shell scripts** for deployment orchestration, rollback, and health checks

## Directory Structure

```
devops/ci-cd/
├── .github/
│   └── workflows/
│       ├── build-and-test.yml      # Build, test, lint, security scan
│       ├── deploy-dev.yml          # Auto-deploy to development
│       ├── deploy-staging.yml      # Deploy to staging (on tags)
│       ├── deploy-prod.yml         # Production deployment (manual approval)
│       ├── security-scan.yml       # Comprehensive security scanning
│       └── dependency-update.yml   # Automated dependency updates
└── scripts/
    ├── build.sh                    # Docker image build script
    ├── test.sh                     # Test execution script
    ├── deploy.sh                   # Deployment orchestration
    ├── rollback.sh                 # Rollback deployments
    └── health-check.sh             # Health check verification
```

## GitHub Actions Workflows

### 1. Build and Test (`build-and-test.yml`)

**Triggers:**
- Push to `main`, `develop`, `feature/**` branches
- Pull requests to `main`, `develop`

**Features:**
- Linting (ESLint, Prettier)
- Multi-version testing (Node 18, 20, 22)
- Unit and integration tests
- Code coverage reports (Codecov)
- Security scanning (npm audit, Snyk, Trivy)
- Docker image building for all services (api, web, worker)
- Container image scanning
- Failure notifications to Slack

**Services Built:**
- API service
- Web service
- Worker service

### 2. Deploy to Development (`deploy-dev.yml`)

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Features:**
- Automatic deployment to development environment
- AWS EKS cluster integration
- Helm/kubectl deployment
- Multiple service deployment (api, web, worker)
- Health checks and smoke tests
- Automatic rollback on failure
- Deployment notifications

**Environment:** Development
**Replicas:** 2 (API, Web), 1 (Worker)

### 3. Deploy to Staging (`deploy-staging.yml`)

**Triggers:**
- Tags matching `v*-staging` (e.g., v1.2.3-staging)
- Manual workflow dispatch with tag input

**Features:**
- Image validation before deployment
- Helm-based deployment with auto-scaling
- Comprehensive integration tests
- Performance testing
- Deployment backup creation
- Automatic rollback on failure
- QA notification

**Environment:** Staging
**Replicas:** 3 (API, Web), 2 (Worker)
**Auto-scaling:** Enabled (3-10 pods)

### 4. Deploy to Production (`deploy-prod.yml`)

**Triggers:**
- Tags matching `v[0-9]+.[0-9]+.[0-9]+` (e.g., v1.2.3)
- Manual workflow dispatch with approval

**Features:**
- **Manual approval required** (production-approval environment)
- Version format validation
- Image security scanning
- Canary/rolling update strategy
- Zero-downtime deployment
- Maintenance mode support
- Pod disruption budgets
- Critical path testing
- Error rate monitoring
- Automatic GitHub release creation
- Multiple notification channels

**Environment:** Production
**Replicas:** 5 (API, Web), 3 (Worker)
**Auto-scaling:** Enabled (5-20 pods for API)

### 5. Security Scanning (`security-scan.yml`)

**Triggers:**
- Daily at 2 AM UTC
- Push/PR to `main` branch
- Manual workflow dispatch

**Security Tools:**
- **Dependency Scanning:** npm audit, Snyk, OWASP Dependency Check
- **Code Analysis:** GitHub CodeQL, Semgrep
- **Secret Scanning:** Trivy, GitLeaks
- **Container Scanning:** Trivy, Snyk, Grype
- **IaC Scanning:** Checkov, tfsec
- **License Compliance:** license-checker, FOSSA
- **Malware Detection:** ClamAV

**Outputs:**
- SARIF reports uploaded to GitHub Security
- Consolidated security report
- Critical findings notifications

### 6. Dependency Updates (`dependency-update.yml`)

**Triggers:**
- Weekly on Monday at 9 AM UTC
- Manual workflow dispatch

**Features:**
- Automated patch/minor version updates
- Auto-merge for Dependabot patches
- Security vulnerability fixes
- Outdated package reports
- Docker base image updates
- npm cache cleanup
- Automated PR creation

## Shell Scripts

### 1. build.sh - Docker Image Build

Build and tag Docker images for all services.

**Usage:**
```bash
./build.sh [OPTIONS]

Options:
  -s, --service SERVICE    Service to build (api|web|worker|all)
  -e, --environment ENV    Environment (dev|staging|prod)
  -v, --version VERSION    Version tag
  -p, --push              Push images to registry
  -c, --cache             Use cache when building
  --platform PLATFORM     Target platform
```

**Examples:**
```bash
# Build API service
./build.sh --service api --version v1.2.3 --push

# Build all services for production
./build.sh --service all --environment prod --version v2.0.0 --push

# Build with cache
./build.sh -s web -e staging -v v1.0.0-rc1 -c
```

**Features:**
- Multi-service support
- Multi-platform builds
- Automatic tagging (version, environment, commit SHA)
- Registry authentication
- Image size reporting
- Build error handling

### 2. test.sh - Test Execution

Run all types of tests with reporting.

**Usage:**
```bash
./test.sh [OPTIONS]

Options:
  -t, --type TYPE         Test type (unit|integration|e2e|smoke|all)
  -e, --environment ENV   Environment (test|dev|staging)
  -c, --coverage         Generate coverage report
  -p, --parallel         Run tests in parallel
  -v, --verbose          Verbose output
  -w, --watch           Watch mode
  --bail                Stop on first failure
  --timeout SECONDS     Test timeout
```

**Examples:**
```bash
# Run all tests with coverage
./test.sh --type all --coverage

# Run integration tests
./test.sh --type integration --environment staging

# Run unit tests in watch mode
./test.sh -t unit -w
```

**Test Types:**
- Unit tests
- Integration tests
- End-to-end tests
- Smoke tests
- Linting
- Type checking

### 3. deploy.sh - Deployment Orchestration

Deploy services to Kubernetes clusters.

**Usage:**
```bash
./deploy.sh SERVICE ENVIRONMENT VERSION [OPTIONS]

Options:
  --dry-run         Perform a dry run
  --helm           Use Helm for deployment
  --kubectl        Use kubectl for deployment
  --rollback       Rollback on failure
  --force          Force deployment
  --skip-health    Skip health checks
```

**Examples:**
```bash
# Deploy API to development
./deploy.sh api dev v1.2.3

# Deploy all services to production
./deploy.sh all production v2.0.0

# Dry run deployment
./deploy.sh web staging v1.5.0-rc1 --dry-run
```

**Features:**
- Multi-cluster support (dev, staging, production)
- Helm and kubectl deployment methods
- Image verification
- Namespace management
- Environment-specific configurations
- Rollout status monitoring
- Health check integration
- Automatic rollback on failure

### 4. rollback.sh - Deployment Rollback

Rollback deployments to previous versions.

**Usage:**
```bash
./rollback.sh ENVIRONMENT [SERVICE] [OPTIONS]

Options:
  --revision REVISION  Rollback to specific revision
  --helm              Use Helm for rollback
  --kubectl           Use kubectl for rollback
  --dry-run           Show what would be rolled back
  --no-wait           Don't wait for rollout
```

**Examples:**
```bash
# Rollback API in production
./rollback.sh production api

# Rollback all services in staging
./rollback.sh staging all

# Rollback to specific revision
./rollback.sh production web --revision 3
```

**Features:**
- Production safety confirmation
- Deployment history display
- Automatic backup creation
- Helm and kubectl support
- Rollout verification
- Health check validation
- Notification integration

### 5. health-check.sh - Health Verification

Perform comprehensive health checks on deployed services.

**Usage:**
```bash
./health-check.sh ENVIRONMENT [SERVICE] [OPTIONS]

Options:
  --timeout SECONDS   Timeout for health checks
  --interval SECONDS  Check interval
  --strict           Fail on any warning
  --quick            Quick health check only
```

**Examples:**
```bash
# Check API health in production
./health-check.sh production api

# Quick check all services in staging
./health-check.sh staging all --quick

# Strict health check
./health-check.sh production web --strict --timeout 600
```

**Health Checks:**
- Pod status and readiness
- Deployment status
- Service endpoints
- HTTP health endpoints
- Resource usage (CPU, memory)
- Recent log errors
- Overall system health

## Required Secrets

Configure these secrets in GitHub repository settings:

### Registry & Authentication
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `DOCKER_PASSWORD` - Docker registry password (if not using GitHub registry)
- `DOCKER_USERNAME` - Docker registry username

### AWS Credentials
- `AWS_ROLE_ARN` - AWS IAM role for development/staging
- `AWS_PROD_ROLE_ARN` - AWS IAM role for production
- `AWS_REGION` - AWS region (e.g., us-east-1)

### Database & Services
- `STAGING_DATABASE_URL` - Staging database connection string
- `STAGING_REDIS_URL` - Staging Redis connection string
- `STAGING_API_KEY` - Staging API key
- `PROD_DATABASE_URL` - Production database connection string
- `PROD_REDIS_URL` - Production Redis connection string
- `PROD_API_KEY` - Production API key
- `PROD_JWT_SECRET` - Production JWT secret

### Security Scanning
- `SNYK_TOKEN` - Snyk API token
- `CODECOV_TOKEN` - Codecov upload token
- `FOSSA_API_KEY` - FOSSA license scanning API key

### Notifications
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications

## Environment Configuration

### Development
- **Namespace:** `development`
- **Replicas:** 2 (API, Web), 1 (Worker)
- **Auto-scaling:** Disabled
- **Resources:** Low (250m CPU, 256Mi RAM)

### Staging
- **Namespace:** `staging`
- **Replicas:** 3 (API, Web), 2 (Worker)
- **Auto-scaling:** Enabled (3-10 pods)
- **Resources:** Medium (500m CPU, 512Mi RAM)

### Production
- **Namespace:** `production`
- **Replicas:** 5 (API, Web), 3 (Worker)
- **Auto-scaling:** Enabled (5-20 pods)
- **Resources:** High (1000m CPU, 1Gi RAM)
- **Pod Disruption Budget:** Enabled
- **Manual Approval:** Required

## Deployment Flow

### Development Deployment
```
Push to main → Build & Test → Deploy to Dev → Health Checks → Notification
```

### Staging Deployment
```
Create v*-staging tag → Validate → Build → Deploy to Staging → Integration Tests → Notification
```

### Production Deployment
```
Create v* tag → Validate → Manual Approval → Build → Canary Deploy → Health Checks →
Performance Tests → Update DNS → Notification → GitHub Release
```

## Rollback Strategy

1. **Automatic Rollback:** Triggered on deployment failure
2. **Manual Rollback:** Using `rollback.sh` script
3. **Helm Rollback:** To previous release
4. **kubectl Rollback:** To previous revision

## Monitoring & Notifications

### Slack Notifications
- Build failures
- Deployment success/failure
- Security findings
- Rollback events

### Health Monitoring
- Kubernetes readiness/liveness probes
- HTTP health endpoints
- Resource usage tracking
- Error log monitoring

## Best Practices

1. **Never skip tests** in production deployments
2. **Always review** staging deployments before production
3. **Use semantic versioning** for releases (v1.2.3)
4. **Monitor deployments** for at least 15 minutes after production release
5. **Keep secrets encrypted** in GitHub Secrets
6. **Review security scan results** before merging PRs
7. **Update dependencies** regularly via automated PRs
8. **Test rollback procedures** in staging environment

## Troubleshooting

### Build Failures
- Check Docker daemon status
- Verify Dockerfile syntax
- Check build logs in Actions tab

### Deployment Failures
- Verify cluster connectivity: `kubectl cluster-info`
- Check namespace: `kubectl get ns`
- Review pod logs: `kubectl logs -n <namespace> <pod-name>`
- Check events: `kubectl get events -n <namespace>`

### Health Check Failures
- Verify service is running: `kubectl get pods -n <namespace>`
- Check service endpoints: `kubectl get endpoints -n <namespace>`
- Review application logs
- Test health endpoint manually

### Rollback Issues
- Check deployment history: `helm history <release>` or `kubectl rollout history deployment/<name>`
- Verify previous version is available
- Check cluster resources

## Contributing

When adding new services or modifying the pipeline:

1. Update relevant workflow files
2. Test in development environment first
3. Update this README with changes
4. Create PR with detailed description
5. Ensure all checks pass before merging

## License

Internal use only - Proprietary
