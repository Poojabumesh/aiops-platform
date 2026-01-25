# ECR Repository for RCA Lambda
resource "aws_ecr_repository" "rca_lambda" {
  name                 = "${var.app_name}-rca-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for RCA Lambda
resource "aws_iam_role" "rca_lambda" {
  name = "${var.app_name}-rca-lambda-role"

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

# IAM Policy for RCA Lambda
resource "aws_iam_role_policy" "rca_lambda_policy" {
  name = "${var.app_name}-rca-lambda-policy"
  role = aws_iam_role.rca_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:ListTasks",
          "ecs:StopTask"
        ]
        Resource = "*"
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

# RCA Lambda Function
resource "aws_lambda_function" "rca" {
  function_name = "${var.app_name}-rca"
  role          = aws_iam_role.rca_lambda.arn
  
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.rca_lambda.repository_url}:latest"
  
  timeout       = 120
  memory_size   = 512

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.anomaly_alerts.arn
      ROLLBACK_FUNCTION_NAME = aws_lambda_function.rollback.function_name
    }
  }
}

# Trigger RCA Lambda from Anomaly Detection Lambda
resource "aws_lambda_permission" "allow_anomaly_lambda" {
  statement_id  = "AllowExecutionFromAnomalyLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rca.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = aws_lambda_function.anomaly_detector.arn
}

# Output
output "rca_lambda_ecr_url" {
  value = aws_ecr_repository.rca_lambda.repository_url
}
