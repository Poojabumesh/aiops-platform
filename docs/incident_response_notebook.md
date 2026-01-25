# Incident Response Playbook

## Automated Response Flow
```
Anomaly Detected
      ↓
  RCA Lambda Triggered
      ↓
  Root Cause Identified
      ↓
┌─────┴─────┬─────────┬──────────┐
│           │         │          │
HIGH CPU  MEMORY   ERROR    TIMEOUT
          LEAK     RATE
│           │         │          │
↓           ↓         ↓          ↓
Scale Up  Restart  Rollback   Scale Up
          Tasks   Deploy
```

## Response Matrix

| Root Cause | Severity | Auto Action | Manual Action Required |
|-----------|----------|-------------|----------------------|
| High CPU (no errors) | MEDIUM | Scale up +1 task | Monitor for 15min |
| High CPU (with errors) | HIGH | Scale up +1 task | Investigate code |
| Memory Leak (OOM) | CRITICAL | Restart tasks | Fix memory leak |
| High Error Rate (<10 errors) | HIGH | Alert only | Check logs |
| High Error Rate (>10 errors) | CRITICAL | **Rollback deployment** | Investigate |
| Slow Response | MEDIUM | Scale up | Check dependencies |

## Manual Intervention Steps

### 1. Check CloudWatch Dashboard
```bash
# Open dashboard
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=aiops-platform-enhanced-dashboard
```

### 2. Review Recent Deployments
```bash
# Check deployment history
aws ecs describe-services \
  --cluster aiops-platform-cluster \
  --services aiops-platform-service \
  --query 'services[0].{deployments:deployments,events:events[0:10]}'
```

### 3. Manual Rollback (if auto-rollback failed)
```bash
# Get previous task definition
aws ecs list-task-definitions \
  --family-prefix aiops-platform-task \
  --sort DESC \
  --max-results 5

# Rollback to specific version
aws ecs update-service \
  --cluster aiops-platform-cluster \
  --service aiops-platform-service \
  --task-definition aiops-platform-task:PREVIOUS_VERSION
```

### 4. Manual Scale Up
```bash
# Scale to 4 tasks
aws ecs update-service \
  --cluster aiops-platform-cluster \
  --service aiops-platform-service \
  --desired-count 4
```

### 5. Manual Task Restart
```bash
# Stop all tasks (will auto-restart)
aws ecs list-tasks \
  --cluster aiops-platform-cluster \
  --service-name aiops-platform-service \
  --query 'taskArns' \
  --output text | xargs -I {} aws ecs stop-task \
  --cluster aiops-platform-cluster \
  --task {} \
  --reason "Manual restart during incident"
```

## Post-Incident Analysis

After automated remediation:

1. **Verify Resolution** (15 minutes after remediation)
```bash
   # Check metrics returned to normal
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ECS \
     --metric-name CPUUtilization \
     --dimensions Name=ServiceName,Value=aiops-platform-service \
     --start-time $(date -u -v-30M +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
```

2. **Review RCA Report** - Check email for detailed root cause

3. **Document Incident** - Add to incident log

4. **Update Baselines** (if behavior changed legitimately)
```bash
   cd scripts
   python create_baseline_stats.py
```

## Escalation Path

If automated remediation fails:

1. **Immediate** → On-call engineer (automated email sent)
2. **15 minutes** → Team lead
3. **30 minutes** → Engineering manager
4. **1 hour** → Incident commander

## Testing the System

### Test Anomaly Detection
```bash
python scripts/generate_anomaly.py $ALB_DNS
```

### Test RCA Lambda
```bash
aws lambda invoke \
  --function-name aiops-platform-rca \
  --payload '{"anomalies":["CPU: 60% (expected 4%)"],"metrics":{"cpu_utilization":60}}' \
  response.json
```

### Test Rollback
```bash
aws lambda invoke \
  --function-name aiops-platform-rollback \
  --payload '{"cluster":"aiops-platform-cluster","service":"aiops-platform-service","reason":"Test"}' \
  response.json
```
