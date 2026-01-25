# ECR Repository for Rollback Lambda
resource "aws_ecr_repository" "rollback_lambda" {
  name                 = "${var.app_name}-rollback-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Rollback Lambda
resource "aws_iam_role" "rollback_lambda" {
  name = "${var.app_name}-rollback-lambda-role"

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

# IAM Policy for Rollback Lambda
resource "aws_iam_role_policy" "rollback_lambda_policy" {
  name = "${var.app_name}-rollback-lambda-policy"
  role = aws_iam_role.rollback_lambda.id

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
          "ecs:DescribeServices",
          "ecs:UpdateService",
          "ecs:ListTaskDefinitions",
          "ecs:DescribeTaskDefinition"
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

# Rollback Lambda Function
resource "aws_lambda_function" "rollback" {
  function_name = "${var.app_name}-rollback"
  role          = aws_iam_role.rollback_lambda.arn
  
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.rollback_lambda.repository_url}:latest"
  
  timeout       = 180
  memory_size   = 512

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.anomaly_alerts.arn
    }
  }
}

# Allow RCA Lambda to invoke Rollback Lambda
resource "aws_lambda_permission" "allow_rca_invoke_rollback" {
  statement_id  = "AllowExecutionFromRCALambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rollback.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = aws_lambda_function.rca.arn
}

# Output
output "rollback_lambda_ecr_url" {
  value = aws_ecr_repository.rollback_lambda.repository_url
}
