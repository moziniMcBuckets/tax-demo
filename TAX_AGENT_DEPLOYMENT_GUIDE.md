# Tax Document Agent - Deployment Guide

## Prerequisites

Before deploying, ensure you have:

- ✅ Node.js 20+ installed
- ✅ AWS CLI configured (`aws configure`)
- ✅ AWS CDK CLI installed (`npm install -g aws-cdk`)
- ✅ Python 3.11+ installed
- ✅ Docker running (`docker ps` should work)
- ✅ AWS account with sufficient permissions

---

## Step 1: Configuration (5 minutes)

### 1.1 Copy Configuration File

```bash
cd infra-cdk
cp config-tax-agent.yaml config.yaml
```

### 1.2 Update Configuration

Edit `config.yaml`:

```yaml
stack_name_base: tax-agent  # Change to your preferred name (max 35 chars)

admin_user_email: your-email@example.com  # Optional: auto-create admin user

backend:
  pattern: strands-single-agent
  deployment_type: docker

ses:
  from_email: noreply@yourdomain.com  # Update with your verified email
  verified_domain: yourdomain.com     # Update with your domain
```

### 1.3 Verify SES Email (Important!)

Before deployment, verify your SES email address:

```bash
# Verify email address
aws ses verify-email-identity --email-address noreply@yourdomain.com

# Check verification status
aws ses get-identity-verification-attributes \
  --identities noreply@yourdomain.com
```

**Note:** Check your email for verification link from AWS.

---

## Step 2: Install Dependencies (2 minutes)

```bash
# Install CDK dependencies
npm install

# Verify installation
npm list --depth=0
```

---

## Step 3: Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK in your AWS account/region
cdk bootstrap

# This creates:
# - S3 bucket for CDK assets
# - IAM roles for CloudFormation
# - ECR repository for Docker images
```

**Note:** Only run this once per AWS account/region.

---

## Step 4: Deploy Infrastructure (10-15 minutes)

### 4.1 Synthesize CloudFormation Template

```bash
# Generate CloudFormation template
cdk synth

# This validates your CDK code and generates templates
```

### 4.2 Deploy All Stacks

```bash
# Deploy all stacks (Cognito, Backend, Frontend)
cdk deploy --all

# Or deploy with auto-approval (no prompts)
cdk deploy --all --require-approval never
```

**What Gets Deployed:**
1. Cognito User Pool and clients
2. 4 DynamoDB tables
3. S3 bucket for client documents
4. 5 Gateway Lambda functions
5. AgentCore Gateway with tool targets
6. AgentCore Memory
7. AgentCore Runtime (Docker build + push to ECR)
8. EventBridge automation
9. CloudWatch monitoring
10. Amplify Hosting app

**Deployment Time:** 10-15 minutes (Docker build takes longest)

### 4.3 Monitor Deployment

Watch the deployment progress:
- CloudFormation stacks being created
- Docker image being built and pushed
- Resources being provisioned

---

## Step 5: Deploy Frontend (5 minutes)

```bash
# Return to root directory
cd ..

# Deploy frontend to Amplify
python scripts/deploy-frontend.py
```

This script:
- Generates `aws-exports.json` from stack outputs
- Installs npm dependencies
- Builds Next.js frontend
- Deploys to Amplify Hosting

**Output:** You'll see the frontend URL

---

## Step 6: Create Cognito User (If Needed)

### Option A: Auto-Created (if you set admin_user_email)

Check your email for temporary password and login URL.

### Option B: Manual Creation

1. Go to [AWS Cognito Console](https://console.aws.amazon.com/cognito/)
2. Find your User Pool: `tax-agent-user-pool`
3. Click "Users" tab
4. Click "Create user"
5. Fill in:
   - Email: your-email@example.com
   - Temporary password: (create one)
   - Mark email as verified: ✅
6. Click "Create user"

---

## Step 7: Access the Application

1. Open the Amplify URL from deployment output
2. Sign in with Cognito credentials
3. Change temporary password on first login
4. Start using the tax document agent!

---

## Step 8: Seed Test Data (Optional)

```bash
# Create sample clients and documents for testing
python scripts/seed-test-data.py
```

This creates:
- 5 sample clients
- Document requirements for each
- Sample follow-up history

---

## Verification Steps

### Verify Gateway Tools

```bash
# Test Gateway connectivity
python scripts/test-gateway.py

# Expected output:
# ✅ Gateway URL retrieved
# ✅ OAuth token obtained
# ✅ Tools listed: 5 tools found
# ✅ Sample tool invocation successful
```

### Verify Agent

```bash
# Test agent interaction
python scripts/test-agent.py

# Try queries like:
# - "Show me the status of all clients"
# - "Check documents for client John Smith"
# - "Send a reminder to client Jane Doe"
```

### Verify DynamoDB Tables

```bash
# List tables
aws dynamodb list-tables | grep tax-agent

# Expected tables:
# - tax-agent-clients
# - tax-agent-documents
# - tax-agent-followups
# - tax-agent-settings
```

### Verify S3 Bucket

```bash
# List buckets
aws s3 ls | grep tax-agent

# Expected:
# tax-agent-client-docs-<account-id>
```

---

## Post-Deployment Configuration

### Configure Email Templates

1. Log into the application
2. Go to Settings → Email Templates
3. Customize the 3 reminder templates
4. Save changes

### Add Clients

1. Go to Clients → Add New Client
2. Fill in client information
3. Select document requirements
4. Save client

### Test Automation

Wait for 9 AM the next weekday, or manually trigger:

```bash
# Manually invoke daily check
aws lambda invoke \
  --function-name tax-agent-daily-check \
  --payload '{}' \
  response.json

cat response.json
```

---

## Monitoring

### CloudWatch Dashboard

```bash
# Open dashboard
aws cloudwatch get-dashboard \
  --dashboard-name tax-agent-costs
```

Or visit: AWS Console → CloudWatch → Dashboards → `tax-agent-costs`

### View Logs

```bash
# Gateway logs
aws logs tail /aws/bedrock-agentcore/gateway/tax-agent-gateway --follow

# Runtime logs
aws logs tail /aws/bedrock-agentcore/runtime/tax-agent_TaxAgent --follow

# Lambda logs
aws logs tail /aws/lambda/tax-agent-document-checker --follow
```

### Check Costs

```bash
# View estimated charges
aws cloudwatch get-metric-statistics \
  --namespace AWS/Billing \
  --metric-name EstimatedCharges \
  --dimensions Name=Currency,Value=USD \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Maximum
```

---

## Troubleshooting

### Issue: Docker build fails

**Solution:**
```bash
# Ensure Docker is running
docker ps

# On Mac with Docker Desktop
open -a Docker

# On Mac with Finch
finch vm start
```

### Issue: CDK deploy fails with permissions error

**Solution:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Ensure you have admin permissions or these specific permissions:
# - CloudFormation full access
# - IAM role creation
# - Lambda, DynamoDB, S3, Cognito, Bedrock permissions
```

### Issue: SES email not sending

**Solution:**
```bash
# Verify email address
aws ses verify-email-identity --email-address noreply@yourdomain.com

# Check if in sandbox mode
aws ses get-account-sending-enabled

# Request production access if needed
# https://console.aws.amazon.com/ses/home#/account
```

### Issue: Gateway returns "Unauthorized"

**Solution:**
```bash
# Check machine client credentials in SSM
aws ssm get-parameter --name /tax-agent/machine_client_id

# Verify Cognito configuration
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> \
  --client-id <client-id>
```

### Issue: Agent not responding

**Solution:**
```bash
# Check Runtime logs
aws logs tail /aws/bedrock-agentcore/runtime/tax-agent_TaxAgent --follow

# Check Runtime status
aws bedrock-agentcore describe-runtime \
  --runtime-identifier <runtime-arn>
```

---

## Cleanup

To remove all resources:

```bash
cd infra-cdk
cdk destroy --all --force
```

**Warning:** This will delete:
- All DynamoDB tables (client data will be lost)
- S3 bucket (documents will be deleted)
- All Lambda functions
- AgentCore resources
- Cognito User Pool (users will be deleted)

**Note:** DynamoDB tables have `RETAIN` removal policy, so they won't be deleted automatically. You'll need to delete them manually if desired.

---

## Cost Monitoring

### Set Up Budget Alerts

```bash
# Create monthly budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json
```

**budget.json:**
```json
{
  "BudgetName": "tax-agent-monthly",
  "BudgetType": "COST",
  "TimeUnit": "MONTHLY",
  "BudgetLimit": {
    "Amount": "20",
    "Unit": "USD"
  }
}
```

### Expected Costs

| Scale | Clients | Cost/Season | Cost/Month |
|-------|---------|-------------|------------|
| Small | 50 | $8.13 | $2.03 |
| Medium | 500 | $70.10 | $17.53 |
| Large | 5,000 | $701 | $175.25 |

---

## Next Steps After Deployment

1. **Customize Agent** - Update system prompt in `patterns/strands-single-agent/`
2. **Add Clients** - Import client list or add manually
3. **Configure Templates** - Customize email templates
4. **Test Workflow** - Run through complete document collection flow
5. **Monitor Costs** - Watch CloudWatch dashboard
6. **Scale Up** - Add more clients as needed

---

## Support Resources

- **Planning Documents:** All `TAX_*.md` files in root
- **FAST Documentation:** `docs/` folder
- **AWS AgentCore Docs:** https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html
- **CDK Documentation:** https://docs.aws.amazon.com/cdk/

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-01-24
**Status:** Ready for deployment
