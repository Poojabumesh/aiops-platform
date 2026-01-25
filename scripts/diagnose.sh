#!/bin/bash

echo "=== 1. Check ALB exists ==="
aws elbv2 describe-load-balancers \
  --names aiops-platform-alb \
  --query 'LoadBalancers[0].{State:State.Code,DNS:DNSName}' 2>&1

echo ""
echo "=== 2. Check Target Group Health ==="
TG_ARN=$(aws elbv2 describe-target-groups \
  --names aiops-platform-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text 2>&1)

if [[ $TG_ARN == arn* ]]; then
  aws elbv2 describe-target-health --target-group-arn $TG_ARN
else
  echo "Target group not found"
fi

echo ""
echo "=== 3. Check ECS Service Status ==="
aws ecs describe-services \
  --cluster aiops-platform-cluster \
  --services aiops-platform-service \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount,events:events[0:3]}' 2>&1

echo ""
echo "=== 4. Check Running Tasks ==="
TASK_ARNS=$(aws ecs list-tasks \
  --cluster aiops-platform-cluster \
  --service-name aiops-platform-service \
  --desired-status RUNNING \
  --query 'taskArns' \
  --output text 2>&1)

if [ -n "$TASK_ARNS" ]; then
  for TASK in $TASK_ARNS; do
    echo "Task: $TASK"
    aws ecs describe-tasks \
      --cluster aiops-platform-cluster \
      --tasks $TASK \
      --query 'tasks[0].{status:lastStatus,health:healthStatus,containerHealth:containers[0].healthStatus}'
  done
else
  echo "No running tasks found"
fi

echo ""
echo "=== 5. Check Stopped Tasks (recent failures) ==="
STOPPED_TASK=$(aws ecs list-tasks \
  --cluster aiops-platform-cluster \
  --service-name aiops-platform-service \
  --desired-status STOPPED \
  --max-results 1 \
  --query 'taskArns[0]' \
  --output text 2>&1)

if [[ $STOPPED_TASK == arn* ]]; then
  aws ecs describe-tasks \
    --cluster aiops-platform-cluster \
    --tasks $STOPPED_TASK \
    --query 'tasks[0].{stoppedReason:stoppedReason,stoppedAt:stoppedAt,exitCode:containers[0].exitCode}'
else
  echo "No stopped tasks found"
fi

echo ""
echo "=== 6. Recent CloudWatch Logs ==="
aws logs tail /ecs/aiops-platform --since 10m | tail -30

echo ""
echo "=== DIAGNOSIS ==="
echo "If you see:"
echo "  - No running tasks → Tasks are crashing, check logs above"
echo "  - Target health 'unhealthy' → Health check failing"
echo "  - Exit code 137 → Out of memory (increase to 1024 MB)"
echo "  - No targets → Tasks haven't registered with ALB yet"
