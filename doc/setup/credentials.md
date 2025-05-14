# Credentials Management for Teatime

This document provides guidance on setting up and managing credentials for the Teatime golf booking system, both for local development and AWS deployment.

## Local Development

### Setting Up Your .env File

1. Copy the template configuration file (two options):

```bash
# Option 1: Create .env in project root (recommended)
cp config/.env.example .env

# Option 2: Create .env in config directory
cp config/.env.example config/.env
```

2. Edit the `.env` file with your Club Caddie credentials:

```
CLUB_CADDIE_USERNAME=your_username_here
CLUB_CADDIE_PASSWORD=your_password_here
```

3. Configure additional settings as needed:

```
# Booking Preferences
TARGET_TIME=14:00       # Format: HH:MM in 24-hour time
PLAYER_COUNT=4          # Number of players to book (typically 2-4)

# Runtime Mode
DRY_RUN=true            # Set to false for actual booking

# Debug Settings
DEBUG_INTERACTIVE=false # Set to true for interactive debugging
```

### Credential Security Best Practices

- **Never commit** your `.env` file to version control (it's already in `.gitignore`)
- Use different credentials for testing vs. production
- Regularly update your passwords

## AWS Deployment

For the serverless AWS deployment, credentials will be managed using AWS Secrets Manager.

### Setting Up AWS Secrets Manager

1. Create a secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name teatime/club-caddie-credentials \
    --description "Club Caddie login credentials" \
    --secret-string '{"username":"your_username","password":"your_password"}'
```

2. Update your Lambda function's IAM role to include permission to access this secret:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:region:account-id:secret:teatime/club-caddie-credentials-*"
        }
    ]
}
```

3. In your Lambda function code, retrieve the credentials:

```python
import boto3
import json
import os
from botocore.exceptions import ClientError

def get_secret():
    secret_name = "teatime/club-caddie-credentials"
    region_name = "us-east-1"  # Use your AWS region
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        secret_dict = json.loads(secret)
        return secret_dict['username'], secret_dict['password']
    except ClientError as e:
        # Handle exceptions appropriately
        print(f"Error retrieving secret: {e}")
        raise e

# Use the credentials
username, password = get_secret()
```

### Other Configuration Values

Other configuration values (non-sensitive) should be stored as Lambda Environment Variables:

- `TARGET_TIME`: Target tee time in HH:MM format
- `PLAYER_COUNT`: Number of players to book for
- `DRY_RUN`: Whether to run in dry-run mode
- `MAX_RETRIES`: Number of retry attempts
- `WAIT_AFTER_COMPLETION`: Whether to wait after completion

## Rotation and Maintenance

### Password Updates

When the Club Caddie password changes:

1. **Local Development**: Update your `.env` file with the new password
2. **AWS Deployment**: Update the secret in AWS Secrets Manager:

```bash
aws secretsmanager update-secret \
    --secret-id teatime/club-caddie-credentials \
    --secret-string '{"username":"your_username","password":"your_new_password"}'
```

### Monitoring Access

For AWS deployments, enable CloudTrail logging to monitor access to your secrets:

```bash
aws cloudtrail create-trail \
    --name SecretsManagerTrail \
    --s3-bucket-name your-bucket-name \
    --is-multi-region-trail
    
aws cloudtrail start-logging --name SecretsManagerTrail
```

## Troubleshooting

### Common Credential Issues

1. **Authentication Failures**:
   - Verify credentials are correct in `.env` or Secrets Manager
   - Check if Club Caddie account is locked or requires password reset
   - Try logging in manually to confirm account status

2. **AWS Permissions**:
   - Verify Lambda execution role has appropriate permissions
   - Check CloudWatch logs for access denied errors

3. **Environment Setup**:
   - Ensure `.env` file is in the correct location for local development
   - Verify Lambda environment variables are correctly set
