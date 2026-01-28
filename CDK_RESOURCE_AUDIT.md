# CDK Resource Audit - All Resources Now Managed

## Summary

**All resources are now created and managed by CDK. No manual resource creation required.**

## Resources Created by CDK

### DynamoDB Tables (6 total)
1. ✅ `tax-agent-clients` - Client information
2. ✅ `tax-agent-documents` - Document tracking
3. ✅ `tax-agent-followups` - Follow-up history
4. ✅ `tax-agent-settings` - Accountant settings
5. ✅ `tax-agent-feedback` - User feedback
6. ✅ `tax-agent-usage` - Usage tracking for billing

**All tables have**:
- PAY_PER_REQUEST billing
- Point-in-time recovery enabled
- AWS-managed encryption
- DESTROY removal policy (for dev/test)
- GSIs where needed (accountant_id indexes)

### S3 Buckets (2 total)
1. ✅ `tax-agent-client-docs-{account}` - Client document storage
   - CORS configured for frontend
   - S3 event notifications to DocumentProcessor
   - Auto-delete on stack destroy
   
2. ✅ `tax-agent-staging-bucket` - Amplify deployment staging
   - Created by AmplifyStack
   - Auto-delete on stack destroy

### Lambda Functions (13 total)

**Gateway Tools (7)**:
1. ✅ TaxDocChecker - Check client documents
2. ✅ TaxEmail - Send follow-up emails
3. ✅ TaxStatus - Get client status
4. ✅ TaxEscalate - Escalate clients
5. ✅ TaxReqMgr - Manage requirements
6. ✅ TaxUpload - Generate upload URLs
7. ✅ TaxSendLink - Send upload links

**API Functions (4)**:
8. ✅ FeedbackLambda - Handle feedback submissions
9. ✅ BatchOperationsLambda - Bulk operations
10. ✅ ClientManagementLambda - Client CRUD
11. ✅ BillingLambda - Usage/cost queries

**Utility Functions (2)**:
12. ✅ DocumentProcessor - S3 event handler
13. ✅ ZipPackagerLambda - Package agent code (optional)

### SNS Topics (1 total)
1. ✅ `tax-agent-escalations` - Escalation notifications

### AgentCore Resources (3 total)
1. ✅ Gateway - MCP protocol with JWT auth
2. ✅ Runtime - Docker container deployment
3. ✅ Memory - Conversation persistence

### API Gateway (1 total)
1. ✅ `tax-agent-api` - REST API with endpoints:
   - POST /feedback
   - GET /clients
   - POST /clients
   - POST /batch-operations
   - POST /upload-url
   - GET /download-url/{clientId}/{documentType}
   - POST /requirements
   - GET /billing

### Cognito (1 total)
1. ✅ User Pool with:
   - Self-service sign-up
   - Email verification
   - Machine-to-machine client
   - User pool domain

### Amplify (1 total)
1. ✅ Amplify App - Frontend hosting

## Changes Made

### 1. S3 Bucket Creation
**Before**: Imported existing bucket with `s3.Bucket.fromBucketName()`
**After**: Creates bucket with `new s3.Bucket()` with proper CORS and event notifications

### 2. DynamoDB Tables Creation
**Before**: Tables referenced by name only (expected to exist)
**After**: All 4 tax tables created with proper schemas and GSIs

### 3. SNS Topic Creation
**Before**: Topic ARN constructed (expected to exist)
**After**: Topic created with `new sns.Topic()`

### 4. Proper Dependencies
**Before**: Gateway targets created without waiting for permissions
**After**: Explicit dependencies added:
- Gateway waits for all Lambda functions
- Gateway waits for Gateway role
- Targets wait for Gateway, role, and Lambda

## Deployment Order

1. **Cognito** (separate stack)
2. **DynamoDB Tables** (clients, documents, followups, settings, feedback, usage)
3. **S3 Bucket** (client-docs)
4. **SNS Topic** (escalations)
5. **Lambda Functions** (all 13)
6. **Gateway Role** (with Lambda invoke permissions)
7. **Gateway** (waits for role + Lambdas)
8. **Gateway Targets** (waits for Gateway + role + Lambdas)
9. **Runtime** (independent)
10. **Memory** (independent)
11. **API Gateway** (uses Lambdas)
12. **Amplify** (separate stack)

## Verification Checklist

Before deploying, verify:
- [x] All table schemas defined
- [x] All Lambda functions have proper IAM permissions
- [x] S3 bucket has CORS configuration
- [x] S3 event notifications configured
- [x] SNS topic created
- [x] Gateway dependencies explicit
- [x] No `fromBucketName` or `fromTableName` imports
- [x] All resources have removal policies
- [x] No hardcoded ARNs (except AWS-managed resources)

## What's NOT Created by CDK

**AWS-Managed Resources**:
- Lambda Powertools Layer (AWS-provided)
- Bedrock foundation models (AWS-provided)

**Manual Steps Still Required**:
- SES email verification (one-time)
- Cognito user creation (via Console or CLI)
- SNS spending limit (via Console)

## Deployment Command

```bash
cd infra-cdk
export AWS_REGION=us-west-2
export AWS_DEFAULT_REGION=us-west-2
cdk deploy tax-agent --require-approval never
```

**Expected**: Clean deployment with all resources created in proper order.

## Post-Deployment

```bash
# Seed test data
python3 scripts/seed-tax-test-data.py

# Deploy frontend
python3 scripts/deploy-frontend.py

# Verify email
aws ses verify-email-identity --email-address your-email@domain.com
```

## Summary

✅ All infrastructure is now Infrastructure as Code
✅ No manual resource creation required
✅ Proper dependencies ensure correct deployment order
✅ All resources have removal policies for clean teardown
✅ Ready for deployment
