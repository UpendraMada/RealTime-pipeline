# Real-Time Data Processing Pipeline using AWS and Terraform

## 📌 Problem Statement

E-commerce platforms generate large volumes of **real-time transaction events** such as orders, payments, and activity logs. Traditional batch-oriented systems are not suitable for scenarios where **instant validation, notifications, and data persistence** are required.  

The challenge for this assignment is to build a **real-time data processing pipeline** that can:  

- Ingest continuous e-commerce transactions through a **reliable queueing system (Amazon SQS)** to handle bursts of traffic.  
- Trigger **serverless compute (AWS Lambda)** to process, validate, and enrich transaction data.  
- Persist valid transactions into a **scalable NoSQL database (Amazon DynamoDB)** for low-latency querying and storage.  
- Send **real-time notifications (Amazon SNS)** for specific business scenarios, such as:  
  - Large orders above 1000.  
  - Transactions with missing or invalid data.  
- Monitor system health and performance using **Amazon CloudWatch** logs, metrics, and alarms.  
- Provision all infrastructure components using **Infrastructure as Code (Terraform)**, ensuring reproducibility and maintainability.  


---

## 🛠️ Solution Overview
To solve the above problem, we implemented a **Real-Time Data Processing Pipeline** using AWS managed services, Terraform, and Python.

### 🔄 Data Flow
1. **Producer (Python Script)**  
   - A Python script (`send_test_events.py`) generates and sends test events to Amazon SQS.  
   - Supports parameters like event count, batch size, and target data size.  

2. **Amazon SQS (Queue)**  
   - Acts as a **buffer** for incoming events.  
   - Ensures durability and decouples producers from consumers.  

3. **AWS Lambda (Processor)**  
   - Triggered by new messages in SQS.  
   - Parses, validates, and enriches events.  
   - Reduces payload size if necessary to fit DynamoDB limits.  
   - Writes processed records to DynamoDB.  

4. **Amazon DynamoDB (Storage)**  
   - Stores all processed events for querying and analysis.  
   - Provides **scalable, low-latency** storage for real-time use cases.

5. **Amazon SNS (Notification Service)**
   - Receives published messages from Lambda.
   - Delivers **real-time alerts** (e.g., via email or SMS) to subscribers.
   - Ensures stakeholders are notified when events are successfully processed or if failures occur.

6. **Amazon CloudWatch (Monitoring)**  
   - Tracks logs and metrics for Lambda, SQS, and DynamoDB.  
   - Helps verify successful processing and troubleshoot issues.  

7. **Terraform (Infrastructure as Code)**  
   - Provisions all AWS resources (SQS, Lambda, DynamoDB, IAM roles, etc.).  
   - Ensures reproducibility and version-controlled infrastructure.  

---

## 🚀 Deployment Steps

### 1. Setup Environment
- Install [Terraform](https://www.terraform.io/downloads.html)  
- Configure AWS profile:  
  ```bash
  aws configure --profile rt-pipeline-user

### 2. Deploy Infrastructure
1. Navigate into the Terraform directory: `cd terraform`  
2. Initialize Terraform: `terraform init`  
3. Review the execution plan: `terraform plan`  
4. Apply the changes: `terraform apply`
### 3. Deploy Lambda Function
1. Navigate to the Lambda directory → `cd lambda`  
2. Package the Lambda code → `Compress-Archive -Path * -DestinationPath lambda.zip -Force`  
3. Update the Lambda function with AWS CLI →  
   `aws lambda update-function-code --function-name rt-pipeline-user-processor --zip-file fileb://lambda.zip --profile rt-pipeline-user --region us-east-1`
### 4.Send Test Events
python tools/send_test_events.py \
  --queue-url "https://sqs.us-east-1.amazonaws.com/<account-id>/rt-pipeline-user-orders" \
  --count 26000 \
  --batch-size 10 \
  --target-kb 200 \
  --rate 0
### 5. Verify Processing

SQS: Check metrics to confirm messages are consumed.

Lambda Logs:

aws logs tail /aws/lambda/rt-pipeline-user-processor --since 15m --follow


DynamoDB: Scan table for inserted items via console or AWS CLI.
## 📊 Monitoring
- **CloudWatch Logs** → Lambda execution details  
- **CloudWatch Metrics** → SQS queue depth, Lambda invocations, DynamoDB throughput  
- **DynamoDB Console** → Verify item count and storage size  

## ✅ Key Learnings
- Built a real-time event-driven pipeline on AWS  
- Automated infrastructure with Terraform  
- Learned to handle large payloads and DynamoDB storage limits  
- Gained experience in monitoring serverless architectures  

## 🔮 Future Enhancements
- Stream processed data to Amazon S3 or Redshift for analytics  
- Add error handling with DLQ (Dead Letter Queue)  
- Implement unit tests and CI/CD pipeline for automated deployments  

