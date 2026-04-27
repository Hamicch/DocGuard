output "api_gateway_url" {
  description = "Base URL for the deployed API Gateway HTTP API."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Lambda function name."
  value       = aws_lambda_function.api.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN."
  value       = aws_lambda_function.api.arn
}
