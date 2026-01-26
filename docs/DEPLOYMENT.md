# Deployment Guide - Tax Document Agent

## Prerequisites

### Required Software:
- Node.js 20+ ([download](https://nodejs.org/))
- Python 3.11+ ([download](https://python.org/))
- Docker ([download](https://docker.com/))
- AWS CLI ([install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- AWS CDK: `npm install -g aws-cdk`

### AWS Account:
- Active AWS account
- Admin permissions (or sufficient IAM permissions)
- AWS CLI configured: `aws configure`

---

## Configuration

### 1. Update config.yaml

```bash
cd infra-cdk
cp config-tax-agent.yaml config.yaml
```

Edit `config.yaml`:
```yaml
stack_name_base: your-stack-name  # Max 35 characters
admin_user_email: your-email@domain.com  # Optional
backend:
  pattern: strands-single-agent
  deployment_type: docker
```

---

## Deployment Steps

### 1. Install Dependencies (2 minutes)

```bash
cd infra-cdk
npm install
```

### 2. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

This creates CDK resources in your AWS account.

### 3. Deploy Infrastructure (10-15 minutes)

```bash
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2
cdk deploy --all --require-approval never
```

**What gets deployed:**
- 8 Lambda functions (7 Gateway tools + Document Processor)
- 5 DynamoDB tables
- S3 bucket with CORS and event notifications
- AgentCore Gateway, Runtime, Memory
- Cognito User Pool
- Amplify app
- API Gateway with /clients, /upload-url, /feedback endpoints
- SNS, EventBridge, CloudWatch

### 4. Deploy Frontend (5 minutes)

```bash
cd ..
python3 scripts/deploy-frontend.py
```

**Output:** Frontend URL (save this)

### 5. Configure Email (5 minutes)

```bash
# Verify your email for sending
aws ses verify-email-identity --email-address your-email@domain.com

# Check your email and click verification link

# Verify it worked
aws ses get-identity-verification-attributes --identities your-email@domain.com

# Update Lambda with verified email
aws lambda update-function-configuration \
  --function-name $(aws lambda list-functions --query 'Functions[?contains(FunctionName, `TaxEmail`)].FunctionName' --output text | head -1) \
  --environment "Variables={CLIENTS_TABLE=<stack-name>-clients,FOLLOWUP_TABLE=<stack-name>-followups,SETTINGS_TABLE=<stack-name>-settings,SES_FROM_EMAIL=your-email@domain.com}"
```

### 6. Add IAM Permissions (5 minutes)

Run the permission script to grant Lambda functions access to DynamoDB, S3, and SES:

```bash
python3 scripts/add-lambda-permissions.py
```

This adds permissions for all 8 Lambda functions:
- TaxDocChecker, TaxEmail, TaxStatus, TaxEscalate
- TaxReqMgr, TaxUpload, TaxSendLink, DocumentProcessor

### 7. Create User (2 minutes)

**Via AWS Console:**
1. Go to Cognito → User Pools
2. Find: `<stack-name>-user-pool`
3. Create user with your email
4. Mark email as verified

**Via CLI:**
```bash
aws cognito-idp admin-create-user \
  --user-pool-id <pool-id> \
  --username your-email@domain.com \
  --user-attributes Name=email,Value=your-email@domain.com Name=email_verified,Value=true \
  --message-action SUPPRESS
```

---

## Post-Deployment

### 1. Seed Test Data

```bash
python3 scripts/seed-tax-test-data.py
```

Creates 5 test clients with different statuses.

### 2. Test Gateway Tools

```bash
python3 scripts/test-all-gateway-tools.py
```

Verifies all 6 tools are working.

### 3. Test Frontend

1. Open your Amplify URL
2. Log in with Cognito user
3. Try queries:
   - "Show me all my clients" (accountant ID: acc_test_001)
   - "Which clients are at risk?"
   - "Send a reminder to Mohamed Mohamud"

---

## Verification Checklist

- [ ] All CloudFormation stacks: CREATE_COMPLETE
- [ ] 7 Lambda functions deployed
- [ ] 5 DynamoDB tables created
- [ ] S3 bucket created
- [ ] Gateway has 6 targets
- [ ] Frontend accessible
- [ ] SES email verified
- [ ] Cognito user created
- [ ] Test data seeded
- [ ] Gateway tools tested
- [ ] Agent responds in frontend

---

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.

### Quick Fixes:

**"CDK deploy fails"**
- Ensure Docker is running: `docker ps`
- Check AWS credentials: `aws sts get-caller-identity`

**"Frontend not loading"**
- Wait 2-3 minutes after deployment
- Check Amplify console for build status

**"Agent not responding"**
- Verify Runtime is deployed
- Check CloudWatch logs
- Ensure Gateway URL in SSM

**"Emails not sending"**
- Verify SES email: `aws ses get-identity-verification-attributes`
- Check Lambda environment variables
- Review SES sandbox limits

---

## Cleanup

To remove all resources:

```bash
cd infra-cdk
cdk destroy --all --force
```

**Warning:** This deletes all data including:
- Client records
- Uploaded documents
- Follow-up history

DynamoDB tables have RETAIN policy and must be deleted manually if desired.

---

## Next Steps

1. **Production Setup:**
   - Verify your domain in SES
   - Move out of SES sandbox
   - Add real clients
   - Customize email templates

2. **Monitoring:**
   - Check CloudWatch dashboard
   - Review costs daily
   - Monitor email delivery rates

3. **Customization:**
   - Update agent system prompt
   - Customize email templates
   - Add your branding

---

**Deployment Time:** 15-20 minutes
**Difficulty:** Intermediate
**Cost:** $3.86/season for 50 clients
