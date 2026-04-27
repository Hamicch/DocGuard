locals {
  resource_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_iam_role" "lambda_exec" {
  name = "${local.resource_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.resource_prefix}-api"
  retention_in_days = 14
}

resource "aws_lambda_function" "api" {
  function_name = "${local.resource_prefix}-api"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  filename      = var.lambda_zip_path
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      ENVIRONMENT               = var.environment
      LOG_LEVEL                 = var.log_level
      SUPABASE_URL              = var.supabase_url
      SUPABASE_ANON_KEY         = var.supabase_anon_key
      SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key
      SUPABASE_JWT_SECRET       = var.supabase_jwt_secret
      DATABASE_URL              = var.database_url
      GITHUB_APP_ID             = var.github_app_id
      GITHUB_APP_PRIVATE_KEY    = var.github_app_private_key
      GITHUB_WEBHOOK_SECRET     = var.github_webhook_secret
      LLM_API_KEY               = var.llm_api_key
      LLM_BASE_URL              = var.llm_base_url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.lambda,
  ]
}
