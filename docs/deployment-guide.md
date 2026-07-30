# Aegis AI — Deployment Guide

## Prerequisites

- AWS account with appropriate IAM permissions
- Docker and Docker Compose v2.20+
- kubectl configured for your cluster
- Terraform v1.7+
- Helm v3.14+

## Infrastructure Provisioning

### 1. Initialize Terraform

```bash
cd terraform/environments/production
terraform init
```

### 2. Plan and Apply

```bash
terraform plan -var="db_password=$(openssl rand -base64 32)"
terraform apply
```

This provisions:
- VPC with public/private subnets across 3 AZs
- EKS cluster with managed node groups (general + GPU for AI workloads)
- RDS PostgreSQL 16 with pgvector, Multi-AZ, encryption
- ElastiCache Redis cluster with encryption
- Security groups with least-privilege access

### 3. Configure kubectl

```bash
aws eks update-kubeconfig --name aegis-production --region us-east-1
```

## Application Deployment

### 1. Create Secrets

```bash
kubectl create namespace aegis

kubectl create secret generic aegis-secrets -n aegis \
  --from-literal=DATABASE_PASSWORD='...' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --from-literal=ANTHROPIC_API_KEY='sk-ant-...' \
  --from-literal=JWT_SECRET_KEY="$(openssl rand -base64 48)" \
  --from-literal=SLACK_BOT_TOKEN='xoxb-...' \
  --from-literal=JIRA_API_TOKEN='...'
```

### 2. Deploy with Kustomize

```bash
kubectl apply -k k8s/overlays/production/
```

### 3. Verify Deployment

```bash
kubectl get pods -n aegis
kubectl rollout status deployment/aegis-api -n aegis
curl -s https://api.aegis.your-org.com/health | jq
```

### 4. Run Migrations

```bash
kubectl exec -it deployment/aegis-api -n aegis -- alembic upgrade head
```

### 5. Seed Demo Data (Optional)

```bash
kubectl exec -it deployment/aegis-api -n aegis -- python -m app.db.seed
```

## Monitoring Setup

Grafana dashboards are auto-provisioned. Access at `https://grafana.aegis.your-org.com`.

Pre-configured dashboards:
- **API Performance**: Request rates, latencies (p50/p95/p99), error rates
- **AI Operations**: Agent run durations, LLM token usage, tool call frequency
- **Infrastructure**: CPU/memory utilization, pod health, database connections

## Production Checklist

### Security
- [ ] TLS certificates configured (cert-manager + Let's Encrypt)
- [ ] OAuth2 providers configured
- [ ] API rate limiting enabled
- [ ] WAF rules applied
- [ ] Secrets stored in AWS Secrets Manager / Vault
- [ ] Network policies restricting pod-to-pod communication
- [ ] Pod security policies enforced
- [ ] Audit logging enabled and forwarded to SIEM

### Reliability
- [ ] Horizontal Pod Autoscaler configured
- [ ] Pod Disruption Budgets set
- [ ] Database backups verified (automated + cross-region)
- [ ] Redis persistence configured
- [ ] Health check endpoints returning correct status
- [ ] Circuit breakers on external API calls
- [ ] Retry policies with exponential backoff

### Observability
- [ ] Prometheus scraping all services
- [ ] Grafana dashboards provisioned
- [ ] Alert rules configured (PagerDuty/Slack integration)
- [ ] Distributed tracing enabled (Jaeger/OTLP)
- [ ] Structured logging with correlation IDs
- [ ] Error tracking configured (Sentry integration)

### Performance
- [ ] Database connection pooling tuned
- [ ] Redis caching strategy implemented
- [ ] CDN configured for static assets
- [ ] API response compression enabled
- [ ] Database indexes verified with EXPLAIN ANALYZE
- [ ] Load testing completed at 2x expected peak
