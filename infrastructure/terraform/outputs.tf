output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "DNS name of the load balancer"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "ECR repository URL"
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.main.name
  description = "ECS cluster name"
}

output "ecs_service_name" {
  value       = aws_ecs_service.app.name
  description = "ECS service name"
}

output "ecs_task_definition_family" {
  value       = aws_ecs_task_definition.app.family
  description = "ECS task definition family name"
}

output "container_name" {
  value       = "${var.app_name}-container"
  description = "Container name in task definition"
}

output "enhanced_dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.enhanced.dashboard_name}"
}

output "anomaly_lambda_ecr_url" {
  value = aws_ecr_repository.anomaly_lambda.repository_url
}
