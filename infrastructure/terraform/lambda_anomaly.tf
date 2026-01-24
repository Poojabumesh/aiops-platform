# S3 Bucket for ML Model
resource "aws_s3_bucket" "ml_models" {
  bucket = "${var.app_name}-ml-models-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id
  versioning_configuration {
    status = "Enabled"
  }
}

# SNS Topic for Anomaly Alerts
resource "aws_sns_topic" "anomaly_alerts" {
  name = "${var.app_name}-anomaly-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.anomaly_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email 
}

# IAM Role for Lambda
resource "aws_iam_role" "anomaly_lambda" {
  name = "${var.app_name}-anomaly-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "anomaly_lambda_policy" {
  name = "${var.app_name}-anomaly-lambda-policy"
  role = aws_iam_role.anomaly_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.ml_models.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.anomaly_alerts.arn
      }
    ]
  })
}

# Lambda Function

#create s3 bucket for lambda zip
resource "aws_s3_bucket" "lambda_artifacts" {
  bucket = "${var.app_name}-lambda-artifacts-${data.aws_caller_identity.current.account_id}"
  }

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration { status = "Enabled" }
  }

resource "aws_ecr_repository" "anomaly_lambda" {
  name                 = "${var.app_name}-anomaly-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_lambda_function" "anomaly_detector" {
  function_name = "${var.app_name}-anomaly-detector"
  role          = aws_iam_role.anomaly_lambda.arn
  
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.anomaly_lambda.repository_url}:lambda-docker-20260124-091834"

  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      MODEL_BUCKET  = aws_s3_bucket.ml_models.id
      SNS_TOPIC_ARN = aws_sns_topic.anomaly_alerts.arn
    }
  }
}

# EventBridge Rule to trigger every 5 minutes
resource "aws_cloudwatch_event_rule" "anomaly_detection_schedule" {
  name                = "${var.app_name}-anomaly-detection"
  description         = "Trigger anomaly detection every 5 minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "anomaly_lambda" {
  rule      = aws_cloudwatch_event_rule.anomaly_detection_schedule.name
  target_id = "AnomalyDetectorLambda"
  arn       = aws_lambda_function.anomaly_detector.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.anomaly_detector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.anomaly_detection_schedule.arn
}

# Get AWS account ID
data "aws_caller_identity" "current" {}

# Outputs
output "ml_models_bucket" {
  value = aws_s3_bucket.ml_models.id
}

output "sns_topic_arn" {
  value = aws_sns_topic.anomaly_alerts.arn
}

