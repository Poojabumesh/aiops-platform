#!/bin/bash

echo "=== Phase 4 Verification ==="
echo ""

# 1. Check model in S3
echo "1. Model in S3:"
BUCKET=$(cd infrastructure/terraform && terraform output -raw ml_models_bucket)
aws s3 ls s3://$BUCKET/models/

# 2. Check Lambda function exists
echo ""
echo "2. Lambda function:"
aws lambda get-function --function-name aiops-platform-anomaly-detector \
  --query 'Configuration.{State:State,Runtime:Runtime,Timeout:Timeout}'

# 3. Check EventBridge rule
echo ""
echo "3. EventBridge schedule:"
aws events describe-rule --name aiops-platform-anomaly-detection \
  --query '{State:State,Schedule:ScheduleExpression}'

# 4. Check SNS subscription
echo ""
echo "4. SNS subscription:"
TOPIC_ARN=$(cd infrastructure/terraform && terraform output -raw sns_topic_arn)
aws sns list-subscriptions-by-topic --topic-arn $TOPIC_ARN \
  --query 'Subscriptions[0].{Endpoint:Endpoint,Status:SubscriptionArn}'

# 5. Recent Lambda executions
echo ""
echo "5. Recent Lambda executions:"
aws logs tail /aws/lambda/aiops-platform-anomaly-detector --since 1h | grep -E "Starting|ANOMALY|No anomaly" | tail -5

echo ""
echo "=== Verification Complete ==="
