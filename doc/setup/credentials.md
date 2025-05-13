# Credentials Management

## Development Environment

### Using .env Files

For local development, we'll use a `.env` file to store sensitive credentials. This file **should never be committed to version control**.

1. Create a `.env` file in the root directory:

```bash
# Tea Time .env file

# Club Caddie Credentials
CLUB_CADDIE_USERNAME="your_username"
CLUB_CADDIE_PASSWORD="your_password"

# AWS Configuration (for local development)
AWS_PROFILE="teatime"
AWS_REGION="us-east-1" # Or your preferred region
```

2. Add `.env` to your `.gitignore` file:

```
# .gitignore
.env
*.env
```

3. Load environment variables in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env

username = os.environ.get("CLUB_CADDIE_USERNAME")
password = os.environ.get("CLUB_CADDIE_PASSWORD")
```

### Required Packages

Install the dotenv package to use this approach:

```bash
pip install python-dotenv
```

## Production Environment

### AWS Secrets Manager

For the production environment, we'll store credentials securely in AWS Secrets Manager:

1. Create a secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name tea-time/club-caddie \
    --description "Club Caddie login credentials" \
    --secret-string '{"username":"your_username","password":"your_password"}'
```

2. Update IAM roles to allow Lambda functions to access this secret.

3. Retrieve secrets in Lambda functions:

```python
import boto3
import json

def get_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='tea-time/club-caddie')
    secret = json.loads(response['SecretString'])
    return secret['username'], secret['password']
```

### Infrastructure as Code

When deploying with CloudFormation or AWS CDK, define the secret as part of your stack:

```python
# Example using AWS CDK
from aws_cdk import aws_secretsmanager as secretsmanager

credentials_secret = secretsmanager.Secret(self, "ClubCaddieCredentials",
    secret_name="tea-time/club-caddie",
    description="Club Caddie login credentials"
)

# Grant the Lambda function access to the secret
credentials_secret.grant_read(booking_lambda)
```

## Security Best Practices

1. **Never commit credentials** to Git repositories
2. **Limit access** to secrets based on the principle of least privilege
3. **Rotate credentials** periodically
4. **Monitor access** to secrets via CloudTrail
5. **Use environment-specific secrets** for dev, staging, and production

## Additional Configuration

For advanced configuration needs beyond simple credentials:

1. **Parameter Store** for less sensitive configuration:
```python
import boto3

ssm = boto3.client('ssm')
response = ssm.get_parameter(Name='/tea-time/config/preferred-time', WithDecryption=False)
preferred_time = response['Parameter']['Value']
```

2. **App Config** for feature flags and configuration management