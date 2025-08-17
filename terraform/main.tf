terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = ">= 5.0" }
    archive = { source = "hashicorp/archive", version = ">= 2.4" }
  }
}

provider "aws" { region = var.region }

locals { name = var.project }

# DynamoDB
resource "aws_dynamodb_table" "orders" {
  name         = "${local.name}-orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  point_in_time_recovery { enabled = true }
  tags = { Project = local.name }
}

# Dead Letter Queue
resource "aws_sqs_queue" "orders_dlq" {
  name                      = "${local.name}-orders-dlq"
  message_retention_seconds = 1209600
  tags                      = { Project = local.name }
}

# Main Queue
resource "aws_sqs_queue" "orders" {
  name                       = "${local.name}-orders"
  visibility_timeout_seconds = 60
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.orders_dlq.arn
    maxReceiveCount     = 3
  })
  tags = { Project = local.name }
}

# SNS Topics
resource "aws_sns_topic" "txn_alerts" {
  name = "${local.name}-txn-alerts"
  tags = { Project = local.name }
}

resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"
  tags = { Project = local.name }
}

# Subscriptions
resource "aws_sns_topic_subscription" "txn_email" {
  count     = length(var.txn_email) > 0 ? 1 : 0
  topic_arn = aws_sns_topic.txn_alerts.arn
  protocol  = "email"
  endpoint  = var.txn_email
}

resource "aws_sns_topic_subscription" "alarms_email" {
  count     = length(var.alarm_email) > 0 ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# IAM Role for Lambda
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid     = "Logs"
    actions = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:*:*:*"]
  }
  statement {
    sid     = "SQS"
    actions = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility", "sqs:DeleteMessageBatch"]
    resources = [aws_sqs_queue.orders.arn]
  }
  statement {
    sid     = "DDB"
    actions = ["dynamodb:PutItem", "dynamodb:DescribeTable"]
    resources = [aws_dynamodb_table.orders.arn]
  }
  statement {
    sid     = "SNS"
    actions = ["sns:Publish"]
    resources = [aws_sns_topic.txn_alerts.arn, aws_sns_topic.alarms.arn]
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name   = "${local.name}-lambda-policy"
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Lambda Packaging
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/../lambda.zip"
}

# Lambda Function
resource "aws_lambda_function" "processor" {
  function_name = "${local.name}-processor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  filename      = data.archive_file.lambda_zip.output_path
  timeout       = 30
  memory_size   = 256
  environment {
    variables = {
      DDB_TABLE     = aws_dynamodb_table.orders.name
      SNS_TOPIC_ARN = aws_sns_topic.txn_alerts.arn
      ALERT_AMOUNT  = tostring(var.alert_amount)
    }
  }
  depends_on = [aws_iam_role_policy_attachment.lambda_attach]
}

# Event Source Mapping
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.orders.arn
  function_name                      = aws_lambda_function.processor.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
  depends_on                         = [aws_lambda_function.processor]
}

# Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  dimensions          = { FunctionName = aws_lambda_function.processor.function_name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "dlq_visible" {
  alarm_name          = "${local.name}-dlq-has-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  dimensions          = { QueueName = aws_sqs_queue.orders_dlq.name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "ddb_throttles" {
  alarm_name          = "${local.name}-ddb-throttled-writes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  dimensions          = { TableName = aws_dynamodb_table.orders.name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}
