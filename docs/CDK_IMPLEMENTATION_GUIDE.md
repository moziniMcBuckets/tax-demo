# CDK Implementation Guide

**CRITICAL RULE:** All backend infrastructure changes MUST be done through AWS CDK. Never use AWS CLI for infrastructure modifications.

---

## Why CDK-Only?

### Benefits:
✅ **Version Control** - All infrastructure changes tracked in Git  
✅ **Reproducibility** - Deploy identical infrastructure anywhere  
✅ **Code Review** - Infrastructure changes reviewed like code  
✅ **Rollback** - Easy to revert to previous versions  
✅ **Documentation** - Infrastructure is self-documenting  
✅ **Testing** - Can test infrastructure changes before deployment  
✅ **Consistency** - No configuration drift  

### Problems with CLI:
❌ **No history** - Changes not tracked  
❌ **Not reproducible** - Can't recreate in another account  
❌ **No review** - Changes made without oversight  
❌ **Configuration drift** - CDK and actual state diverge  
❌ **Hard to debug** - No clear source of truth  

---

## CDK Architecture

### Stack Structure

```
tax-agent (Main Stack)
├── tax-agent-cognito (Nested Stack)
│   ├── User Pool
│   ├── User Pool Client
│   └── User Pool Domain
├── tax-agent-backend (Nested Stack)
│   ├── AgentCore Gateway
│   ├── AgentCore Runtime
│   ├── AgentCore Memory
│   ├── 8 Lambda Functions
│   ├── API Gateway
│   ├── S3 Bucket Configuration
│   └── IAM Roles & Policies
└── tax-agent-amplify (Nested Stack)
    ├── Amplify App
    ├── Amplify Branch
    └── S3 Staging Bucket
```

### File Organization

```
infra-cdk/
├── bin/
│   └── tax-agent-cdk.ts          # Entry point
├── lib/
│   ├── tax-agent-main-stack.ts   # Main orchestrator
│   ├── cognito-stack.ts          # Authentication
│   ├── backend-stack.ts          # Core backend (Gateway, Runtime, Lambda)
│   ├── tax-agent-backend-stack.ts # Tax-specific extensions
│   ├── amplify-hosting-stack.ts  # Frontend hosting
│   └── utils/
│       ├── config-manager.ts     # Configuration management
│       └── agentcore-role.ts     # IAM role utilities
├── lambdas/
│   └── feedback/                 # API Gateway Lambda functions
└── config-tax-agent.yaml         # Deployment configuration
```

---

## Adding New Features

### 1. Adding a New Gateway Tool

**Steps:**

1. **Create Lambda function code:**
```bash
mkdir -p gateway/tools/my_new_tool
touch gateway/tools/my_new_tool/my_tool_lambda.py
touch gateway/tools/my_new_tool/requirements.txt
touch gateway/tools/my_new_tool/tool_spec.json
```

2. **Add to CDK (`infra-cdk/lib/backend-stack.ts`):**
```typescript
// In createAgentCoreGateway method, add to taxLambdas array:
{
  id: "TaxMyTool",
  handler: "my_tool_lambda.lambda_handler",
  path: "my_new_tool",
  env: { 
    CLIENTS_TABLE: clientsTableName,
    // Add other env vars
  },
  targetName: "my-tool",  // SHORT name (< 10 chars)
  specPath: "my_new_tool"
},
```

3. **Add IAM permissions in CDK:**
```typescript
// Permissions are automatically granted via:
// - this.taxLambdaFunctions stored in class
// - addToRolePolicy() calls in configureClientDocumentsBucket()
// - Or add specific permissions inline
```

4. **Deploy:**
```bash
cd infra-cdk
cdk deploy tax-agent
```

**DO NOT:**
- ❌ Create Lambda via CLI: `aws lambda create-function`
- ❌ Add permissions via CLI: `aws lambda add-permission`
- ❌ Update config via CLI: `aws lambda update-function-configuration`

### 2. Adding API Gateway Endpoints

**Steps:**

1. **Add endpoint in CDK (`infra-cdk/lib/backend-stack.ts`):**
```typescript
// In createFeedbackApi method:
const myResource = api.root.addResource("my-endpoint")
const myLambda = this.taxLambdaFunctions['TaxMyTool']

myResource.addMethod("POST", new apigateway.LambdaIntegration(myLambda), {
  authorizer,  // For authenticated endpoints
  authorizationType: apigateway.AuthorizationType.COGNITO,
})

// Or for public endpoints:
myResource.addMethod("POST", new apigateway.LambdaIntegration(myLambda), {
  authorizationType: apigateway.AuthorizationType.NONE,
})
```

2. **Update CORS if needed:**
```typescript
// In RestApi configuration:
defaultCorsPreflightOptions: {
  allowOrigins: [frontendUrl, "http://localhost:3000"],
  allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowHeaders: ["Content-Type", "Authorization"],
},
```

3. **Deploy:**
```bash
cdk deploy tax-agent
```

**DO NOT:**
- ❌ Create API via CLI: `aws apigateway create-rest-api`
- ❌ Add methods via CLI: `aws apigateway put-method`

### 3. Modifying S3 Buckets

**Steps:**

1. **Update bucket configuration in CDK:**
```typescript
// In configureClientDocumentsBucket method:
const clientBucket = s3.Bucket.fromBucketName(
  this,
  "ClientDocumentsBucket",
  bucketName
);

// Add lifecycle rules
new cr.AwsCustomResource(this, 'BucketLifecycle', {
  onCreate: {
    service: 'S3',
    action: 'putBucketLifecycleConfiguration',
    parameters: {
      Bucket: bucketName,
      LifecycleConfiguration: {
        Rules: [/* your rules */]
      }
    },
    physicalResourceId: cr.PhysicalResourceId.of(`${bucketName}-lifecycle`)
  },
  policy: cr.AwsCustomResourcePolicy.fromStatements([
    new iam.PolicyStatement({
      actions: ['s3:PutLifecycleConfiguration'],
      resources: [`arn:aws:s3:::${bucketName}`]
    })
  ])
});
```

2. **Deploy:**
```bash
cdk deploy tax-agent
```

**DO NOT:**
- ❌ Configure via CLI: `aws s3api put-bucket-cors`
- ❌ Add lifecycle via CLI: `aws s3api put-bucket-lifecycle-configuration`

### 4. Updating DynamoDB Tables

**Steps:**

1. **Modify table in CDK:**
```typescript
// Tables are referenced by name, not created in current CDK
// To add GSI or modify:
const table = dynamodb.Table.fromTableName(
  this,
  "ImportedTable",
  `${config.stack_name_base}-clients`
);

// Add GSI via custom resource if needed
```

2. **For new tables:**
```typescript
const newTable = new dynamodb.Table(this, "NewTable", {
  tableName: `${config.stack_name_base}-new-table`,
  partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
```

3. **Deploy:**
```bash
cdk deploy tax-agent
```

**DO NOT:**
- ❌ Create table via CLI: `aws dynamodb create-table`
- ❌ Update table via CLI: `aws dynamodb update-table`

### 5. Managing IAM Permissions

**Steps:**

1. **Add permissions in CDK:**
```typescript
// For Lambda functions:
myLambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: ['dynamodb:GetItem', 'dynamodb:PutItem'],
    resources: [`arn:aws:dynamodb:${this.region}:${this.account}:table/my-table`]
  })
);

// For service roles:
const role = new iam.Role(this, 'MyRole', {
  assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
});

role.addToPolicy(
  new iam.PolicyStatement({
    actions: ['s3:GetObject'],
    resources: ['arn:aws:s3:::my-bucket/*']
  })
);
```

2. **Deploy:**
```bash
cdk deploy tax-agent
```

**DO NOT:**
- ❌ Attach policies via CLI: `aws iam attach-role-policy`
- ❌ Put role policy via CLI: `aws iam put-role-policy`
- ❌ Use scripts like `add-lambda-permissions.py` (deprecated)

---

## Common Patterns

### Pattern 1: Adding Environment Variables

**Correct (CDK):**
```typescript
const myLambda = new lambda.Function(this, 'MyFunction', {
  // ... other config
  environment: {
    TABLE_NAME: tableName,
    BUCKET_NAME: bucketName,
    API_KEY: secretValue,
  },
});
```

**Incorrect (CLI):**
```bash
# ❌ DON'T DO THIS
aws lambda update-function-configuration \
  --function-name my-function \
  --environment "Variables={TABLE_NAME=my-table}"
```

### Pattern 2: Configuring S3 Events

**Correct (CDK):**
```typescript
new cr.AwsCustomResource(this, 'S3EventNotification', {
  onCreate: {
    service: 'S3',
    action: 'putBucketNotificationConfiguration',
    parameters: {
      Bucket: bucketName,
      NotificationConfiguration: {
        LambdaFunctionConfigurations: [{
          LambdaFunctionArn: myLambda.functionArn,
          Events: ['s3:ObjectCreated:*']
        }]
      }
    },
    physicalResourceId: cr.PhysicalResourceId.of(`${bucketName}-notification`)
  },
  policy: cr.AwsCustomResourcePolicy.fromStatements([
    new iam.PolicyStatement({
      actions: ['s3:PutBucketNotification'],
      resources: [`arn:aws:s3:::${bucketName}`]
    })
  ])
});
```

**Incorrect (CLI):**
```bash
# ❌ DON'T DO THIS
aws s3api put-bucket-notification-configuration \
  --bucket my-bucket \
  --notification-configuration file://config.json
```

### Pattern 3: Updating Lambda Code

**Correct (CDK):**
```typescript
// Code is automatically updated when you deploy
const myLambda = new lambda.Function(this, 'MyFunction', {
  code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/my_tool')),
  // ... other config
});

// Deploy updates the code automatically
```

**Incorrect (CLI):**
```bash
# ❌ DON'T DO THIS
aws lambda update-function-code \
  --function-name my-function \
  --zip-file fileb://function.zip
```

---

## Deployment Workflow

### Standard Deployment

```bash
# 1. Make changes to CDK code
vim infra-cdk/lib/backend-stack.ts

# 2. Test locally (optional)
cd infra-cdk
npm run build

# 3. Deploy
cdk deploy tax-agent --require-approval never

# 4. Verify
aws lambda list-functions --query 'Functions[?contains(FunctionName, `tax-agent`)].FunctionName'
```

### Deployment with Changes

```bash
# 1. Check what will change
cdk diff tax-agent

# 2. Review changes carefully

# 3. Deploy
cdk deploy tax-agent

# 4. Monitor CloudFormation
aws cloudformation describe-stack-events --stack-name tax-agent --max-items 10

# 5. Verify deployment
aws cloudformation describe-stacks --stack-name tax-agent --query 'Stacks[0].StackStatus'
```

### Rollback

```bash
# If deployment fails, CDK automatically rolls back
# To manually rollback to previous version:
git revert HEAD
cdk deploy tax-agent
```

---

## Debugging

### Viewing Resources (CLI is OK)

```bash
# ✅ These are fine - read-only operations
aws lambda list-functions
aws dynamodb list-tables
aws s3 ls
aws logs tail /aws/lambda/my-function --follow
aws cloudformation describe-stacks
```

### Modifying Resources (Use CDK)

```bash
# ❌ NEVER do these via CLI
aws lambda update-function-configuration
aws dynamodb update-table
aws s3api put-bucket-policy
aws iam attach-role-policy
```

---

## Migration Plan

### Deprecating CLI Scripts

**Current scripts that should NOT be used for infrastructure:**
- ❌ `scripts/add-lambda-permissions.py` - Deprecated, use CDK
- ❌ `scripts/configure-s3-cors.py` - Deprecated, use CDK

**Scripts that are still valid (data operations):**
- ✅ `scripts/seed-tax-test-data.py` - Data seeding
- ✅ `scripts/test-*.py` - Testing
- ✅ `scripts/generate-*.py` - Code generation
- ✅ `scripts/deploy-frontend.py` - Frontend deployment

### Updating Existing Infrastructure

If you previously used CLI commands, migrate to CDK:

1. **Document current state:**
```bash
aws lambda get-function-configuration --function-name my-function > current-config.json
```

2. **Implement in CDK:**
```typescript
// Add to backend-stack.ts
```

3. **Deploy and verify:**
```bash
cdk deploy tax-agent
# Verify configuration matches
```

4. **Remove CLI scripts:**
```bash
git rm scripts/add-lambda-permissions.py
```

---

## Best Practices

### 1. Use Class Properties for Reusability

```typescript
export class BackendStack extends cdk.NestedStack {
  private taxLambdaFunctions: { [key: string]: lambda.Function } = {};
  
  // Store Lambda functions for reuse
  this.taxLambdaFunctions[tc.id] = fn;
  
  // Reuse later
  const myLambda = this.taxLambdaFunctions['TaxMyTool'];
}
```

### 2. Pass Configuration via Props

```typescript
export interface BackendStackProps extends cdk.NestedStackProps {
  config: AppConfig;
  userPoolId: string;
  frontendUrl: string;  // Pass from parent stack
}

// Use in methods
private myMethod(config: AppConfig, frontendUrl: string): void {
  // Access passed configuration
}
```

### 3. Use Custom Resources for AWS APIs Not in CDK

```typescript
new cr.AwsCustomResource(this, 'MyCustomResource', {
  onCreate: {
    service: 'ServiceName',
    action: 'apiAction',
    parameters: { /* params */ },
    physicalResourceId: cr.PhysicalResourceId.of('unique-id')
  },
  onUpdate: { /* same as onCreate */ },
  policy: cr.AwsCustomResourcePolicy.fromStatements([
    new iam.PolicyStatement({
      actions: ['service:Action'],
      resources: ['*']
    })
  ])
});
```

### 4. Environment Variables from Stack Context

```typescript
// ✅ Good - uses stack context
environment: {
  TABLE_NAME: `${config.stack_name_base}-clients`,
  REGION: this.region,
  ACCOUNT: this.account,
}

// ❌ Bad - hardcoded
environment: {
  TABLE_NAME: 'tax-agent-clients',
  REGION: 'us-west-2',
}
```

### 5. Conditional Resources

```typescript
// Only create if condition met
if (config.features?.enableAnalytics) {
  const analyticsLambda = new lambda.Function(/* ... */);
}
```

---

## Testing CDK Changes

### 1. Synthesize CloudFormation

```bash
cd infra-cdk
cdk synth tax-agent > template.yaml
# Review the generated CloudFormation
```

### 2. Diff Before Deploy

```bash
cdk diff tax-agent
# Shows exactly what will change
```

### 3. Deploy to Test Environment

```bash
# Use different config
cp config-tax-agent.yaml config-test.yaml
# Edit config-test.yaml with test stack name
cdk deploy tax-agent-test
```

### 4. Validate Deployment

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name tax-agent

# Check resources
aws cloudformation list-stack-resources --stack-name tax-agent

# Test functionality
python3 scripts/test-all-gateway-tools.py
```

---

## Common Scenarios

### Scenario 1: Add New Lambda Function

**Task:** Add a new tool for SMS notifications

**Implementation:**
1. Create `gateway/tools/sms_sender/sms_sender_lambda.py`
2. Add to `taxLambdas` array in `backend-stack.ts`
3. Add SNS permissions inline
4. Deploy: `cdk deploy tax-agent`

**Time:** 30 minutes

### Scenario 2: Update Lambda Environment Variable

**Task:** Change SES_FROM_EMAIL for all email-sending Lambdas

**Implementation:**
1. Update `sesFromEmail` variable in `createAgentCoreGateway()`
2. Or update individual Lambda env in `taxLambdas` array
3. Deploy: `cdk deploy tax-agent`

**Time:** 5 minutes

### Scenario 3: Add DynamoDB GSI

**Task:** Add index for querying by email

**Implementation:**
1. Import table: `dynamodb.Table.fromTableName()`
2. Add GSI via custom resource
3. Deploy: `cdk deploy tax-agent`

**Time:** 15 minutes

### Scenario 4: Configure S3 Lifecycle

**Task:** Auto-archive documents after 1 year

**Implementation:**
1. Add lifecycle configuration in `configureClientDocumentsBucket()`
2. Use custom resource for `putBucketLifecycleConfiguration`
3. Deploy: `cdk deploy tax-agent`

**Time:** 20 minutes

---

## Troubleshooting

### Issue: CDK Deploy Fails

**Solution:**
1. Check error message in CloudFormation console
2. Review `cdk diff` output
3. Check for resource name conflicts
4. Verify IAM permissions for CDK execution role

### Issue: Resource Already Exists

**Solution:**
1. Import existing resource: `Resource.fromResourceName()`
2. Or delete resource and let CDK recreate
3. Or use `cdk import` to import into CDK

### Issue: Permission Denied

**Solution:**
1. Check CDK execution role has necessary permissions
2. Add permissions to custom resource policy
3. Verify service-linked roles exist

### Issue: Circular Dependency

**Solution:**
1. Reorder resource creation
2. Use `Fn.getAtt()` for cross-stack references
3. Split into separate stacks if needed

---

## CDK Commands Reference

### Essential Commands

```bash
# Install dependencies
npm install

# Synthesize CloudFormation
cdk synth tax-agent

# Show differences
cdk diff tax-agent

# Deploy stack
cdk deploy tax-agent

# Deploy all stacks
cdk deploy --all

# Destroy stack (careful!)
cdk destroy tax-agent

# List stacks
cdk list

# Bootstrap (one-time)
cdk bootstrap
```

### Advanced Commands

```bash
# Deploy with no approval prompts
cdk deploy tax-agent --require-approval never

# Deploy with specific profile
cdk deploy tax-agent --profile my-profile

# Deploy to specific region
cdk deploy tax-agent --region us-east-1

# Watch mode (auto-deploy on changes)
cdk watch tax-agent

# Import existing resources
cdk import tax-agent
```

---

## Migration Checklist

When migrating CLI-managed resources to CDK:

- [ ] Document current resource configuration
- [ ] Implement in CDK
- [ ] Test in separate environment
- [ ] Deploy to production
- [ ] Verify functionality
- [ ] Remove CLI scripts
- [ ] Update documentation
- [ ] Train team on CDK workflow

---

## Emergency Procedures

### Hotfix via CLI (Last Resort)

If you MUST use CLI for emergency:

1. **Document the change:**
```bash
echo "Emergency fix: Updated Lambda timeout" >> HOTFIX_LOG.md
echo "Command: aws lambda update-function-configuration ..." >> HOTFIX_LOG.md
```

2. **Make the CLI change**

3. **Immediately create CDK implementation:**
```typescript
// Add to CDK within 24 hours
```

4. **Deploy CDK to make it permanent:**
```bash
cdk deploy tax-agent
```

5. **Verify CDK matches reality:**
```bash
cdk diff tax-agent
# Should show no changes
```

---

## Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK API Reference](https://docs.aws.amazon.com/cdk/api/v2/)
- [CDK Patterns](https://cdkpatterns.com/)
- [AWS CloudFormation](https://docs.aws.amazon.com/cloudformation/)

---

**Remember:** Infrastructure as Code is not just a best practice - it's a requirement for this project. All backend changes go through CDK, no exceptions.
