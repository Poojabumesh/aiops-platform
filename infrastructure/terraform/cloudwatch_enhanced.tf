# Enhanced CloudWatch Dashboard with Custom Metrics
resource "aws_cloudwatch_dashboard" "enhanced" {
  dashboard_name = "${var.app_name}-enhanced-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Application Health
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average", label = "Response Time" }],
            [".", "RequestCount", { stat = "Sum", label = "Request Count", yAxis = "right" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Application Performance"
          yAxis = {
            left = {
              label = "Response Time (seconds)"
            }
            right = {
              label = "Request Count"
            }
          }
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count", { stat = "Sum", label = "2xx Success" }],
            [".", "HTTPCode_Target_4XX_Count", { stat = "Sum", label = "4xx Client Error" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum", label = "5xx Server Error" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "HTTP Response Codes"
        }
      },

      # Row 2: ECS Resources
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU Average" }],
            ["...", { stat = "Maximum", label = "CPU Max" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS CPU Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "MemoryUtilization", { stat = "Average", label = "Memory Average" }],
            ["...", { stat = "Maximum", label = "Memory Max" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Memory Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },

      # Row 3: Service Health
      {
        type   = "metric"
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "DesiredTaskCount", { stat = "Average", label = "Desired" }],
            [".", "RunningTaskCount", { stat = "Average", label = "Running" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS Task Count"
        }
      },
      {
        type   = "metric"
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", { stat = "Average", label = "Healthy" }],
            [".", "UnHealthyHostCount", { stat = "Average", label = "Unhealthy" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Target Health"
        }
      },
      {
        type   = "metric"
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "ActiveConnectionCount", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Active Connections"
        }
      }
    ]
  })
}

# Metric Alarms for Phase 4 ML Baseline
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.app_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when error rate is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "${var.app_name}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when memory usage is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = aws_ecs_service.app.name
    ClusterName = aws_ecs_cluster.main.name
  }
}

