variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "dev"
}

variable "app_name" {
  default = "aiops-platform"
}

variable "alert_email" {
  description = "Email address for anomaly alerts"
  type        = string
  default     = "flavormetrics@gmail.com"
}
