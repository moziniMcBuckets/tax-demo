# Troubleshooting Guide - Tax Document Agent

## Overview

This document captures all issues encountered during development and their solutions. Each issue includes:
- Problem description
- Error messages
- Root cause analysis
- Solution
- Prevention tips

---

## Issue #1: CDK CfnGatewayTarget inlinePayload Format Error

**Date:** January 25, 2026
**Severity:** High (Blocks deployment)
**Component:** CDK Infrastructure - AgentCore Gateway Target

### Problem Description

CDK synth fails when creating Gateway targets with the error:
```
CfnSynthesisError: Resolution error: Supplied properties not correct for "CfnGatewayTargetProps"
  targetConfiguration: supplied properties not correct for "TargetConfigurationProperty"
    mcp: supplied properties not correct for "McpTargetConfigurationProperty"
      lambda: supplied properties not correct for "McpLambdaTargetConfigurationProperty"
        toolSchema: supplied properties not correct for "ToolSchemaProperty"
          inlinePayload: {...} should be a list.
```

### Error Messages

**Initial Error:**
```
inlinePayload: {"name":"check_client_documents",...} should be a list.
```

**Confusing Part:**
The error alternated between saying "expected an object" and "should be a list", which made debugging difficult.

### Root Cause

The `CfnGatewayTarget` L1 construct in AWS CDK requires the `inlinePayload` property to be an **array of tool definition objects**, not a single object.

**Incorrect:**
```typescript
toolSchema: {
  inlinePayload: toolSpec  // Single object - WRONG
}
```

**Correct:**
```typescript
toolSchema: {
  inlinePayload: [toolSpec]  // Array of objects - CORRECT
}
```

### Why This Was Confusing

1. **Sample tool had array format in JSON file:**
   - `gateway/tools/sample_tool/tool_spec.json` contained `[{...}]`
   - When loaded, it was already an array
   - Passing it directly worked for sample tool

2. **Tax tools had object format in JSON files:**
   - `gateway/tools/document_checker/tool_spec.json` contained `{...}`
   - When loaded, it was a single object
   - Needed to be wrapped in array: `[toolSpec]`

3. **Error message was misleading:**
   - Sometimes said "expected object"
   - Sometimes said "should be a list"
   - Actual requirement: array of objects

### Solution

**Step 1: Understand the API requirement**
```typescript
// CfnGatewayTarget expects:
toolSchema: {
  inlinePayload: [  // MUST be an array
    {
      name: "tool_name",
      description: "tool description",
      inputSchema: { /* JSON schema */ }
    }
  ]
}
```

**Step 2: Load tool spec correctly**
```typescript
// Load JSON file
const toolSpec = JSON.parse(
  require("fs").readFileSync(
    path.join(__dirname, "../../gateway/tools/document_checker/tool_spec.json"),
    "utf8"
  )
);

// Wrap in array for inlinePayload
const target = new bedrockagentcore.CfnGatewayTarget(this, "Target", {
  // ...
  targetConfiguration: {
    mcp: {
      lambda: {
        lambdaArn: lambdaFunction.functionArn,
        toolSchema: {
          inlinePayload: [toolSpec],  // Array wrapper
        },
      },
    },
  },
  // ...
});
```

**Step 3: Handle both formats**
```typescript
// If tool spec might be array or object:
const toolSpecData = JSON.parse(fs.readFileSync(specPath, "utf8"));
const toolSpec = Array.isArray(toolSpecData) ? toolSpecData[0] : toolSpecData;

// Then wrap in array
toolSchema: {
  inlinePayload: [toolSpec]
}
```

### Additional Fix: Remove Sample Tool

The sample tool from FAST was causing confusion because:
1. Its JSON format was different (array vs object)
2. It wasn't needed for the tax agent
3. It added unnecessary complexity

**Solution:** Remove sample tool entirely and deploy only tax tools.

### Prevention Tips

1. **Always wrap tool specs in array for `inlinePayload`**
   - Even if you have one tool, use `[toolSpec]`
   - CDK expects array format

2. **Standardize tool_spec.json format**
   - Use object format `{name, description, inputSchema}`
   - Don't use array format in JSON files
   - Wrap in array only when passing to CDK

3. **Test CDK synth frequently**
   - Run `cdk synth` after each change
   - Catch errors early
   - Don't wait until full implementation

4. **Read error messages carefully**
   - "should be a list" = needs array
   - Check CDK API documentation for property types
   - Use TypeScript types for guidance

### Verification

After fix, verify with:
```bash
cd infra-cdk
cdk synth --quiet
# Should complete without errors

# Check generated templates
ls -lh cdk.out/*.template.json
```

### Related Issues

- None yet

### References

- AWS CDK Documentation: https://docs.aws.amazon.com/cdk/
- CfnGatewayTarget API: aws-cdk-lib/aws-bedrockagentcore
- AgentCore Gateway Documentation: docs/GATEWAY.md

---

## Issue Template (For Future Issues)

```markdown
## Issue #X: [Brief Title]

**Date:** YYYY-MM-DD
**Severity:** High/Medium/Low
**Component:** [Component Name]

### Problem Description
[What went wrong]

### Error Messages
```
[Exact error messages]
```

### Root Cause
[Why it happened]

### Solution
[How to fix it]

### Prevention Tips
[How to avoid in future]

### Verification
[How to verify fix works]

### Related Issues
[Links to related issues]

### References
[Documentation links]
```

---

## Best Practices for Issue Documentation

1. **Document immediately** - Don't wait until later
2. **Include exact error messages** - Copy-paste full errors
3. **Explain root cause** - Not just the fix
4. **Provide prevention tips** - Help future developers
5. **Add verification steps** - Show how to confirm fix
6. **Link related issues** - Build knowledge base
7. **Update as needed** - Add new information when discovered

---

**Last Updated:** January 25, 2026
**Total Issues Documented:** 1
**Status:** Active troubleshooting document


---

## Issue #2: Lambda Functions Missing Environment Variables

**Date:** January 25, 2026
**Severity:** High (Tools return internal errors)
**Component:** Gateway Lambda Tools

### Problem Description

Gateway tools are callable but return "An internal error occurred" when invoked. The Lambda functions were deployed without the required environment variables (DynamoDB table names, S3 bucket names, etc.).

### Error Messages

```
{
  "result": {
    "content": [{
      "type": "text",
      "text": "An internal error occurred. Please retry later."
    }],
    "isError": true
  }
}
```

### Root Cause

The Lambda functions were created in `createAgentCoreGateway()` method without environment variables. They need:
- `CLIENTS_TABLE` - DynamoDB table name
- `DOCUMENTS_TABLE` - DynamoDB table name
- `FOLLOWUP_TABLE` - DynamoDB table name
- `SETTINGS_TABLE` - DynamoDB table name
- `CLIENT_BUCKET` - S3 bucket name
- `SES_FROM_EMAIL` - Email address for sending
- `ESCALATION_SNS_TOPIC` - SNS topic ARN

### Solution

**Step 1: Get table and bucket references**

The tables and bucket are created in `createTaxDataLayer()` but not returned or stored as class properties. Need to either:
- Return them from the method
- Store as class properties
- Pass them to `createAgentCoreGateway()`

**Step 2: Add environment variables to Lambda functions**

```typescript
const taxDocumentCheckerLambda = new lambda.Function(this, "TaxDocumentChecker", {
  // ... other config
  environment: {
    CLIENTS_TABLE: clientsTable.tableName,
    DOCUMENTS_TABLE: documentsTable.tableName,
    CLIENT_BUCKET: clientBucket.bucketName,
  },
});
```

**Step 3: Grant IAM permissions**

```typescript
clientsTable.grantReadData(taxDocumentCheckerLambda);
documentsTable.grantReadWriteData(taxDocumentCheckerLambda);
clientBucket.grantRead(taxDocumentCheckerLambda);
```

### Prevention Tips

1. **Always set environment variables** when creating Lambda functions
2. **Test Lambda functions individually** before adding to Gateway
3. **Check CloudWatch logs** for actual error messages
4. **Grant proper IAM permissions** for resource access

### Verification

After fix:
```bash
# Check Lambda environment variables
aws lambda get-function-configuration \
  --function-name <function-name> \
  --query 'Environment.Variables'

# Test Gateway tool
python3 scripts/test-tax-gateway.py
```

### Related Issues

- Issue #1: Gateway target configuration

### References

- Lambda environment variables: https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html
- DynamoDB permissions: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/iam-policy-specific-table-indexes.html


---

## Issue #3: Tool Names Exceed 64 Character Limit

**Date:** January 25, 2026
**Severity:** High (Blocks agent from using tools)
**Component:** AgentCore Gateway Tool Names

### Problem Description

Agent fails to use Gateway tools with error:
```
ValidationException: Value 'gateway_requirement-manager-target___update_document_requirements' 
at 'toolConfig.tools.4.member.toolSpec.name' failed to satisfy constraint: 
Member must have length less than or equal to 64
```

### Error Messages

```
data: {"status": "error", "error": "An error occurred (ValidationException) when calling the ConverseStream operation: 1 validation error detected: Value 'gateway_requirement-manager-target___update_document_requirements' at 'toolConfig.tools.4.member.toolSpec.name' failed to satisfy constraint: Member must have length less than or equal to 64"}
```

### Root Cause

**Tool Name Construction:**
- Gateway target name: `requirement-manager-target` (27 chars)
- Delimiter: `___` (3 chars)
- Tool spec name: `update_document_requirements` (28 chars)
- Prefix added by MCP: `gateway_` (8 chars)
- **Total:** 8 + 27 + 3 + 28 = **66 characters** (exceeds 64 limit)

**Bedrock Converse API Limit:**
- Tool names must be ≤ 64 characters
- Gateway-prefixed names exceed this limit

### Solution

**Option 1: Shorten Gateway Target Names**

Change target names to be shorter:
```typescript
// Before:
name: "requirement-manager-target"  // 27 chars

// After:
name: "req-mgr"  // 7 chars
```

**New total:** 8 + 7 + 3 + 28 = 46 characters ✅

**Option 2: Shorten Tool Spec Names**

Change tool names in tool_spec.json:
```json
// Before:
"name": "update_document_requirements"  // 28 chars

// After:
"name": "update_docs"  // 11 chars
```

**New total:** 8 + 27 + 3 + 11 = 49 characters ✅

**Option 3: Remove MCP Prefix**

Configure Gateway to not add `gateway_` prefix (if possible).

**Recommended:** Option 1 (shorten target names) - easier to implement, doesn't break tool spec contracts.

### Implementation

**Step 1: Update Gateway target names in CDK**

```typescript
const taxTools = [
  { id: "DocChecker", name: "doc-check", lambda: taxDocumentCheckerLambda, specPath: "document_checker" },
  { id: "EmailSender", name: "email", lambda: taxEmailSenderLambda, specPath: "email_sender" },
  { id: "StatusTracker", name: "status", lambda: taxStatusTrackerLambda, specPath: "status_tracker" },
  { id: "EscalationMgr", name: "escalate", lambda: taxEscalationManagerLambda, specPath: "escalation_manager" },
  { id: "ReqMgr", name: "req-mgr", lambda: taxRequirementManagerLambda, specPath: "requirement_manager" },
  { id: "UploadMgr", name: "upload", lambda: taxUploadManagerLambda, specPath: "upload_manager" },
];
```

**Step 2: Redeploy**
```bash
cd infra-cdk
cdk deploy tax-agent
```

**Step 3: Verify tool names**
```bash
# Check tool name lengths
python3 -c "
tools = [
    'gateway_doc-check___check_client_documents',
    'gateway_email___send_followup_email',
    'gateway_status___get_client_status',
    'gateway_escalate___escalate_client',
    'gateway_req-mgr___update_document_requirements',
    'gateway_upload___generate_upload_url'
]
for tool in tools:
    print(f'{tool}: {len(tool)} chars')
"
```

### Prevention Tips

1. **Keep target names short** - Use abbreviations
2. **Keep tool spec names concise** - Avoid long descriptive names
3. **Calculate total length** - prefix (8) + target + delimiter (3) + tool name ≤ 64
4. **Test with agent** - Not just Gateway tools directly
5. **Check Bedrock limits** - Tool names, descriptions, schema sizes

### Verification

After fix:
```bash
# Redeploy Gateway targets
cdk deploy tax-agent

# Test agent
# Open frontend and try: "Show me the status of all my clients"
```

### Related Issues

- Issue #1: Gateway target configuration
- Issue #2: Lambda environment variables

### References

- Bedrock Converse API limits: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- Gateway MCP protocol: docs/GATEWAY.md
