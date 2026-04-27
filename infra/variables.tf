variable "project_name" {
  description = "Project/application name used for AWS resource naming."
  type        = string
  default     = "docguard"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "lambda_runtime" {
  description = "Python runtime for the Lambda function."
  type        = string
  default     = "python3.12"
}

variable "lambda_handler" {
  description = "Lambda handler path."
  type        = string
  default     = "src.main.handler"
}

variable "lambda_memory_size" {
  description = "Lambda memory (MB)."
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda timeout (seconds)."
  type        = number
  default     = 60
}

variable "lambda_zip_path" {
  description = "Path to deployment zip file."
  type        = string
}

variable "supabase_url" {
  description = "Supabase project URL."
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anon key."
  type        = string
  sensitive   = true
}

variable "supabase_service_role_key" {
  description = "Supabase service role key."
  type        = string
  sensitive   = true
}

variable "supabase_jwt_secret" {
  description = "Supabase JWT secret."
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "Postgres database URL used by backend."
  type        = string
  sensitive   = true
}

variable "github_app_id" {
  description = "GitHub App ID."
  type        = string
}

variable "github_app_private_key" {
  description = "GitHub App private key in PEM format."
  type        = string
  sensitive   = true
}

variable "github_webhook_secret" {
  description = "GitHub webhook HMAC secret."
  type        = string
  sensitive   = true
}

variable "llm_api_key" {
  description = "LLM provider API key (OpenRouter/OpenAI-compatible)."
  type        = string
  sensitive   = true
}

variable "llm_base_url" {
  description = "Base URL for OpenAI-compatible LLM endpoint."
  type        = string
  default     = "https://openrouter.ai/api/v1"
}

variable "log_level" {
  description = "Application log level."
  type        = string
  default     = "INFO"
}

variable "alarm_topic_arn" {
  description = "Optional SNS topic ARN for CloudWatch alarms."
  type        = string
  default     = ""
}

variable "audit_dispatch_mode" {
  description = "Audit dispatch mode."
  type        = string
  default     = "background"
}

variable "audit_worker_lambda_name" {
  description = "Audit worker lambda name."
  type        = string
  default     = "docguard-audit-worker"
}

variable "audit_sqs_queue_url" {
  description = "Audit SQS queue URL."
  type        = string
}
