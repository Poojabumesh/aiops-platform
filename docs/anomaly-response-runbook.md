# Anomaly Response Runbook

## When You Receive an Anomaly Alert

### 1. Verify the Alert
- Check email for anomaly details
- Note the timestamp and anomaly score
- Review the metrics that triggered it

### 2. Check CloudWatch Dashboard
```bash
# Open dashboard
cd infrastructure/terraform
terraform output enhanced_dashboard_url
```

Look for:
- CPU/Memory spikes
- Error rate increase
- Response time degradation
- Request count anomalies

### 3. Check Application Logs
```bash
# View recent logs
aws logs tail /ecs/aiops-platform --since 30m

# Look for errors
aws logs tail /ecs/aiops-platform --since 30m | grep -i error
```

### 4. Check ECS Task Health
```bash
# Check tasks status
aws ecs describe-services \
  --cluster aiops-platform-cluster \
  --services aiops-platform-service \
  --query 'services[0].{running:runningCount,desired:desiredCount}'

# Check recent events
aws ecs describe-services \
  --cluster aiops-platform-cluster \
  --services aiops-platform-service \
  --query 'services[0].events[0:5]'
```

### 5. Common Anomaly Types

**High CPU (>50%)**
- Check for infinite loops
- Review recent code deployments
- Check for DDoS attack
- Action: Scale up or restart tasks

**High Memory (>80%)**
- Check for memory leaks
- Review application logs for OOM warnings
- Action: Increase task memory or restart

**High Error Rate (>10%)**
- Check application logs for exceptions
- Review recent deployments
- Check dependencies (database, APIs)
- Action: Rollback if recent deployment

**High Response Time (>2s)**
- Check database query performance
- Check external API latency
- Review CPU/Memory usage
- Action: Optimize queries or scale up

### 6. Remediation Actions

**Immediate:**
```bash
# Restart tasks
aws ecs update-service \
  --cluster aiops-platform-cluster \
  --service aiops-platform-service \
  --force-new-deployment

# Scale up
aws ecs update-service \
  --cluster aiops-platform-cluster \
  --service aiops-platform-service \
  --desired-count 4
```

**If issue persists:**
```bash
# Rollback to previous deployment
# (Phase 6 will automate this)
```

### 7. Post-Incident
- Document root cause
- Update monitoring thresholds if false positive
- Retrain ML model with new baseline if behavior changed legitimately
