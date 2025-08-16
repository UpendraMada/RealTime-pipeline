# Real-Time Data Processing Pipeline using AWS and Terraform

## 📌 Problem Statement
Organizations often need to process **real-time user events** (such as transactions, orders, or logs) at scale. Traditional batch processing introduces delays, making it unsuitable for scenarios requiring instant insights or immediate actions.  

The challenge is to:
- Accept continuous user events from producers.  
- Pass them reliably through a queueing system that can handle bursts of traffic.  
- Process messages with scalable serverless compute that can transform or enrich the data.  
- Persist the final data into a NoSQL database for low-latency querying and storage.  
- Build the entire system using **Infrastructure as Code (IaC)** so it can be easily deployed and managed.  

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

5. **Amazon CloudWatch (Monitoring)**  
   - Tracks logs and metrics for Lambda, SQS, and DynamoDB.  
   - Helps verify successful processing and troubleshoot issues.  

6. **Terraform (Infrastructure as Code)**  
   - Provisions all AWS resources (SQS, Lambda, DynamoDB, IAM roles, etc.).  
   - Ensures reproducibility and version-controlled infrastructure.  

---

## 🚀 Deployment Steps

### 1. Setup Environment
- Install [Terraform](https://www.terraform.io/downloads.html)  
- Install [AWS CLI](https://docs.aws.amazon.com/cli/)  
- Configure AWS profile:  
  ```bash
  aws configure --profile rt-pipeline-user

---

## 🚀 Deployment Steps

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
  --count 1000 \
  --batch-size 10 \
  --target-kb 5 \
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
- Add SNS for fan-out processing  
- Stream processed data to Amazon S3 or Redshift for analytics  
- Add error handling with DLQ (Dead Letter Queue)  
- Implement unit tests and CI/CD pipeline for automated deployments  

