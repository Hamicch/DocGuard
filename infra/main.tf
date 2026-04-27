# Intentionally minimal root module file.
# Terraform resources are split by concern:
# - versions.tf (terraform + provider)
# - variables.tf (inputs)
# - lambda.tf (runtime + IAM + env)
# - apigateway.tf (HTTP API integration)
# - observability.tf (CloudWatch alarms)
# - outputs.tf (exported values)
