# Tea Time: System Architecture Overview

## Introduction

Tea Time is a serverless application designed to automate the booking of tee times at a golf club. The application allows users to input their availability and preferences, then automatically books the earliest available tee time on their behalf when the booking window opens (8 days in advance at midnight Central Time).

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
   - EventBridge scheduled rule triggering at midnight CT
   - Python-based Selenium automation for Club Caddie interaction

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
2. **Browser Automation Complexity**: Running Selenium in Lambda requires careful configuration and management.
3. **Cold Start Latency**: Initial Lambda executions may experience cold starts.