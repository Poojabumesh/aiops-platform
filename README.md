# AIOps Platform

[![Deploy to AWS ECS](https://github.com/YOUR-USERNAME/aiops-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR-USERNAME/aiops-platform/actions/workflows/deploy.yml)

## Architecture

Cloud-native AIOps platform for predictive infrastructure monitoring and auto-remediation.

### Phase 1: Foundation ✅
- AWS VPC with multi-AZ subnets
- ECS Fargate cluster
- Application Load Balancer
- CloudWatch observability

### Phase 2: CI/CD ✅
- Automated build and deployment
- GitHub Actions pipeline
- Rolling updates with zero downtime
- Automated testing

## Quick Start

### Prerequisites
- AWS Account
- Terraform >= 1.0
- Docker
- AWS CLI configured

### Deploy Infrastructure
```bash
cd infrastructure/terraform
terraform init
terraform apply
```

### Test the Application
```bash
ALB_DNS=$(terraform output -raw alb_dns_name)
curl http://$ALB_DNS/health
curl http://$ALB_DNS/api/predict
```

### Deploy via CI/CD
```bash
# Simply push to main branch
git add .
git commit -m "Update application"
git push origin main
```

## Monitoring

- **CloudWatch Dashboard**: AWS Console → CloudWatch → Dashboards → aiops-platform-dashboard
- **ECS Service**: AWS Console → ECS → Clusters → aiops-platform-cluster
- **Logs**: AWS Console → CloudWatch → Log groups → /ecs/aiops-platform

## Cost

Estimated monthly cost: ~$32-39

- ECS Fargate: $15-20
- ALB: $16
- CloudWatch: Free tier
- Data transfer: $1-3

## Next Steps

- [ ] Phase 3: Advanced observability (Prometheus, Grafana)
- [ ] Phase 4: ML-based anomaly detection
- [ ] Phase 5: Root cause analysis
- [ ] Phase 6: Predictive maintenance
- [ ] Phase 7: Automated remediation
