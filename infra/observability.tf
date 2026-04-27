resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.resource_prefix}-lambda-errors"
  alarm_description   = "Lambda error count is greater than 0."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = var.alarm_topic_arn != "" ? [var.alarm_topic_arn] : []
  ok_actions    = var.alarm_topic_arn != "" ? [var.alarm_topic_arn] : []
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration_p95" {
  alarm_name          = "${local.resource_prefix}-lambda-duration-p95"
  alarm_description   = "P95 duration is above 20 seconds."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  extended_statistic  = "p95"
  period              = 60
  evaluation_periods  = 3
  threshold           = 20000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = var.alarm_topic_arn != "" ? [var.alarm_topic_arn] : []
  ok_actions    = var.alarm_topic_arn != "" ? [var.alarm_topic_arn] : []
}
