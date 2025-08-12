output "sqs_queue_url" { value = aws_sqs_queue.orders.url }
output "sqs_queue_arn" { value = aws_sqs_queue.orders.arn }
output "sns_topic_arn" { value = aws_sns_topic.txn_alerts.arn }
output "ddb_table_name" { value = aws_dynamodb_table.orders.name }
output "lambda_name" { value = aws_lambda_function.processor.function_name }
