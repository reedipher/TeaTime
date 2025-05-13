# Teatime: System Architecture Overview

## Introduction

Teatime is a serverless application designed to automate the booking of tee times at a golf club using the Club Caddie system. The application allows users to input their availability and preferences, then automatically books the desired tee time on their behalf when the booking window opens (typically 7 days in advance at 6am).

## System Architecture

### Architecture Diagram

```
Frontend (S3 Static Site) -> Amazon Cognito -> API Gateway -> Lambda Functions -> DynamoDB
                                                 ^
                                                 |
EventBridge Scheduler -> Lambda Booking Function -+
        |                         |
        v                         v
Club Caddie Website  <----->  Headless Browser
                                  |
                                  v
                         SNS Notifications -> Email/SMS
```

### Key Components

1. **Frontend**:
   - S3-hosted static website (React or similar framework)
   - User interface for calendar and preferences

2. **Authentication**:
   - Amazon Cognito for user management
   - Restricted to ~8 users (golf group members)

3. **API Layer**:
   - Amazon API Gateway
   - RESTful endpoints for user operations

4. **Backend Processing**:
   - AWS Lambda functions for business logic
   - Separate Lambda function for the tee time booking process
   - Lambda Layer for headless browser dependencies

5. **Database**:
   - Amazon DynamoDB tables for:
     - User profiles and preferences
     - Availability calendar
     - Booking history/status

6. **Automation**:
   - EventBridge scheduled rule triggering at 6am CT (when booking window opens)
   - Python-based Playwright automation for Club Caddie interaction
   - Robust retry logic and fallback mechanisms
   - Comprehensive debugging and logging capabilities

7. **Notifications**:
   - Amazon SNS for real-time booking notifications
   - Email/SMS delivery of booking confirmations

## AWS Free Tier Considerations

The architecture is designed to operate within AWS Free Tier limits:

- **Lambda**: Functions designed to be efficient; well below 1M free requests/month
- **DynamoDB**: Minimal data storage requirements (< 25GB free tier limit)
- **S3**: Static website hosting (< 5GB free tier storage)
- **Cognito**: Small user base (free tier: 50,000 MAUs)
- **EventBridge**: Minimal scheduled events (once daily)
- **SNS/SES**: Low volume of notifications

## Security Considerations

1. **Authentication**: Cognito manages user authentication securely
2. **Credentials**: Golf club credentials stored in AWS Secrets Manager
3. **Access Control**: IAM policies restrict resource access
4. **Data Protection**: No sensitive user data beyond basic preferences

## Scalability

While designed for a small user group, the architecture can scale if needed:

- Frontend scales automatically via S3
- API Gateway and Lambda auto-scale
- DynamoDB can scale read/write capacity

The main limitation would be the browser automation component, which may require optimization for higher volumes.

## Known Limitations

1. **Dependency on Club Caddie Web Interface**: Any changes to the Club Caddie website may require updates to the automation logic.
2. **Browser Automation Complexity**: Running Playwright in Lambda requires careful configuration and management.
3. **Cold Start Latency**: Initial Lambda executions may experience cold starts.
4. **Timing Precision**: AWS EventBridge may have slight variances in exact execution time, requiring buffering before the booking window opens.

## Lambda Implementation Considerations

For the serverless implementation using AWS Lambda, several technical considerations are important:

### Lambda Packaging

1. **Dependencies**: Playwright and its browser dependencies must be packaged as a Lambda Layer due to size constraints.
2. **Browser Binary**: A custom browser binary compatible with the Lambda environment is required.
3. **Deployment Package**: A comprehensive deployment package should include:
   - Core application code
   - Playwright Lambda Layer
   - Browser binary Lambda Layer

### Environment Configuration

1. **Memory Allocation**: At least 1024MB (preferably 2048MB) of memory to ensure adequate performance for browser automation.
2. **Timeout Setting**: 5-minute timeout to accommodate potential delays in website interaction.
3. **Environment Variables**: All configuration stored as Lambda environment variables, with sensitive credentials in AWS Secrets Manager.

### Execution Strategy

1. **Pre-warming**: A small pre-warming function triggered 1 minute before the booking window opens to minimize cold start issues.
2. **Concurrent Execution**: If multiple bookings are needed simultaneously, consider using separate Lambda functions to avoid resource contention.
3. **Backup Strategy**: Secondary Lambda function triggered 30 seconds later as a fallback in case the primary execution fails.

### Monitoring and Debugging

1. **CloudWatch Logs**: Detailed logs including all steps and timing metrics.
2. **Artifact Storage**: Store screenshots and HTML dumps in S3 for later review if debugging is needed.
3. **SNS Alerts**: Real-time notifications of both success and failure cases.
