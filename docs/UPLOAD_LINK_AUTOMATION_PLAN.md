# Upload Link Automation Plan

## Current State

**Manual Process:**
1. Accountant runs: `python3 scripts/generate-upload-token.py --client-id client_001`
2. Script generates token and prints email template
3. Accountant copies template and manually sends email via their email client

**Problem:** Breaks the automation flow - accountant must leave the chat interface

---

## Proposed Solution: Automated Upload Link Tool

### Option 1: New Gateway Tool (Recommended)

Create a new Gateway tool that combines token generation + email sending.

**Benefits:**
- Agent can send upload links via natural language
- Fully automated end-to-end
- Consistent with existing tool architecture
- Audit trail in DynamoDB

**Implementation:**

#### 1. Create New Lambda: `send_upload_link_lambda.py`

**Location:** `gateway/tools/send_upload_link/`

**Functionality:**
```python
def lambda_handler(event, context):
    """
    Generate upload token and send email with upload link.
    
    Args:
        client_id: Client identifier
        days_valid: Token validity (default: 30)
        custom_message: Optional personal message
    
    Returns:
        Success confirmation with token details
    """
    # 1. Generate secure token
    upload_token = secrets.token_urlsafe(32)
    token_expires = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    
    # 2. Update client record in DynamoDB
    clients_table.update_item(
        Key={'client_id': client_id},
        UpdateExpression='SET upload_token = :token, token_expires = :expires',
        ExpressionAttributeValues={
            ':token': upload_token,
            ':expires': token_expires
        }
    )
    
    # 3. Get client info
    client_info = get_client_info(client_id)
    
    # 4. Generate upload URL
    frontend_url = os.environ['FRONTEND_URL']
    upload_url = f"{frontend_url}/upload?client={client_id}&token={upload_token}"
    
    # 5. Personalize email template
    email_body = f"""Dear {client_info['client_name']},

Please upload your tax documents using this secure link:

{upload_url}

This link is valid for {days_valid} days and is unique to you.

Required documents:
- W-2 from all employers
- 1099 forms from all sources
- Prior year tax return

{custom_message if custom_message else ''}

If you have any questions, please contact me.

Best regards,
{client_info.get('accountant_name', 'Your Accountant')}
"""
    
    # 6. Send email via SES
    message_id = ses.send_email(
        Source=SES_FROM_EMAIL,
        Destination={'ToAddresses': [client_info['email']]},
        Message={
            'Subject': {'Data': 'Secure Link to Upload Your Tax Documents'},
            'Body': {'Text': {'Data': email_body}}
        }
    )
    
    # 7. Log to DynamoDB
    log_upload_link_sent(client_id, upload_token, token_expires, message_id)
    
    return {
        'success': True,
        'upload_link_sent': True,
        'recipient': client_info['email'],
        'token_expires': token_expires,
        'upload_url': upload_url  # For agent to show accountant
    }
```

#### 2. Add Tool Schema to CDK

**Location:** `infra-cdk/lib/tax-agent-backend-stack.ts`

```typescript
// Create Lambda
const sendUploadLinkLambda = new lambda.Function(this, 'SendUploadLinkLambda', {
  runtime: lambda.Runtime.PYTHON_3_13,
  architecture: lambda.Architecture.ARM_64,
  handler: 'send_upload_link_lambda.lambda_handler',
  code: lambda.Code.fromAsset(
    path.join(__dirname, '../../gateway/tools/send_upload_link')
  ),
  environment: {
    CLIENTS_TABLE: clientsTable.tableName,
    FOLLOWUP_TABLE: followupsTable.tableName,
    SES_FROM_EMAIL: config.ses_from_email,
    FRONTEND_URL: amplifyApp.defaultDomain,
  },
  timeout: cdk.Duration.seconds(30),
});

// Grant permissions
clientsTable.grantReadWriteData(sendUploadLinkLambda);
followupsTable.grantWriteData(sendUploadLinkLambda);

// Tool schema
const sendUploadLinkToolSchema = {
  name: 'send_upload_link',
  description: 'Generate secure upload token and send email with upload portal link to client',
  inputSchema: {
    type: 'object',
    properties: {
      client_id: {
        type: 'string',
        description: 'Client identifier'
      },
      days_valid: {
        type: 'integer',
        description: 'Number of days the upload link is valid (default: 30)',
        default: 30
      },
      custom_message: {
        type: 'string',
        description: 'Optional personal message to include in email'
      }
    },
    required: ['client_id']
  }
};

// Add to Gateway
const sendUploadLinkTarget = new bedrockagentcore.CfnGatewayTarget(
  this,
  'SendUploadLinkTarget',
  {
    gatewayIdentifier: gateway.attrGatewayId,
    name: 'send-upload-link-target',
    targetType: 'LAMBDA',
    lambdaTargetConfiguration: {
      lambdaArn: sendUploadLinkLambda.functionArn,
      tools: [sendUploadLinkToolSchema]
    }
  }
);
```

#### 3. Update Agent System Prompt

**Location:** `patterns/strands-single-agent/tax_document_agent.py`

Add to tool descriptions:
```python
6. **send_upload_link** - Generate secure upload token and send email with upload portal link
   - Use when: Accountant wants to send client their upload link
   - Parameters: client_id (required), days_valid (optional, default 30), custom_message (optional)
   - Returns: Confirmation with upload URL and expiration date
```

Add to examples:
```python
Example 6: Sending Upload Link
Accountant: "Send John Smith his upload link"
You: [Use send_upload_link tool with client_id="client_001"]
"Upload link sent to john@example.com! Link is valid for 30 days. 
URL: https://yourdomain.com/upload?client=client_001&token=abc123...
John can now upload documents securely."
```

#### 4. Create DynamoDB Table for Upload Link Tracking

**Optional but recommended for audit trail:**

```typescript
const uploadLinksTable = new dynamodb.Table(this, 'UploadLinksTable', {
  tableName: `${config.stack_name_base}-upload-links`,
  partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'sent_date', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PROVISIONED,
  readCapacity: 1,
  writeCapacity: 1,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});
```

**Schema:**
```json
{
  "client_id": "client_001",
  "sent_date": "2026-01-25T12:00:00Z",
  "upload_token": "abc123...",
  "token_expires": "2026-02-24T12:00:00Z",
  "email_sent_to": "john@example.com",
  "ses_message_id": "msg-123",
  "link_used": false,
  "first_upload_date": null,
  "accountant_id": "acc_001"
}
```

---

### Option 2: Extend Email Sender Tool

Modify existing `email_sender_lambda.py` to handle upload link emails.

**Benefits:**
- Reuses existing infrastructure
- Fewer Lambda functions to manage
- Single email tool

**Drawbacks:**
- Mixes concerns (reminders vs upload links)
- More complex Lambda logic
- Harder to maintain

**Implementation:**

Add new tool name to existing Lambda:
```python
if tool_name == "send_followup_email":
    # Existing reminder logic
    pass
elif tool_name == "send_upload_link":
    # New upload link logic
    upload_token = generate_token()
    update_client_token(client_id, upload_token)
    send_upload_link_email(client_id, upload_token)
```

---

### Option 3: Frontend Integration

Add "Send Upload Link" button to Dashboard.

**Benefits:**
- Visual UI for accountants
- No need to ask agent
- Direct action

**Drawbacks:**
- Requires frontend changes
- Less conversational
- Doesn't leverage AI agent

**Implementation:**

```typescript
// In ClientDetailView.tsx
<Button onClick={() => sendUploadLink(client.client_id)}>
  <Mail className="w-4 h-4 mr-2" />
  Send Upload Link
</Button>

async function sendUploadLink(clientId: string) {
  const response = await fetch(`${API_URL}/send-upload-link`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ client_id: clientId })
  });
  // Show success toast
}
```

---

## Recommended Approach

**Implement Option 1 (New Gateway Tool) + Option 3 (Frontend Button)**

**Why:**
- **Option 1** enables conversational AI: "Send upload links to all incomplete clients"
- **Option 3** provides quick action for single clients
- Both use same backend Lambda
- Best of both worlds

---

## Implementation Steps

### Phase 1: Backend (2-3 hours)

1. ✅ Create `gateway/tools/send_upload_link/` directory
2. ✅ Implement `send_upload_link_lambda.py`
3. ✅ Add `requirements.txt` (boto3)
4. ✅ Create `tool_spec.json` with schema
5. ✅ Update CDK stack to deploy Lambda
6. ✅ Add Gateway target configuration
7. ✅ Grant IAM permissions (DynamoDB, SES)
8. ✅ Deploy: `cdk deploy tax-agent`

### Phase 2: Agent Integration (30 minutes)

1. ✅ Update agent system prompt
2. ✅ Add tool examples
3. ✅ Test with agent: "Send John his upload link"
4. ✅ Redeploy agent

### Phase 3: Frontend (Optional, 1-2 hours)

1. ✅ Add API endpoint for upload link
2. ✅ Add button to ClientDetailView
3. ✅ Add success/error toasts
4. ✅ Deploy frontend

### Phase 4: Testing (1 hour)

1. ✅ Test token generation
2. ✅ Test email delivery
3. ✅ Test upload portal with token
4. ✅ Test token expiration
5. ✅ Test audit logging

---

## Usage Examples

### Via AI Agent (Conversational)

```
Accountant: "Send John Smith his upload link"
Agent: "Upload link sent to john@example.com! The link is valid for 30 days."

Accountant: "Send upload links to all incomplete clients"
Agent: "Sending upload links to 5 clients... Done! Links sent to:
- John Smith (john@example.com)
- Jane Doe (jane@example.com)
- Bob Johnson (bob@example.com)
- Alice Williams (alice@example.com)
- Charlie Brown (charlie@example.com)"

Accountant: "Send Mary her link with a note that I need it by Friday"
Agent: "Upload link sent to mary@example.com with your custom message!"
```

### Via Dashboard (Visual)

```
1. Open client detail view
2. Click "Send Upload Link" button
3. See success toast: "Upload link sent to john@example.com"
4. Link appears in activity log
```

---

## Benefits of Full Automation

✅ **Faster onboarding** - Send links immediately when client signs up  
✅ **Bulk operations** - "Send links to all new clients"  
✅ **Consistent messaging** - Standardized email templates  
✅ **Audit trail** - All links logged in DynamoDB  
✅ **No context switching** - Stay in chat interface  
✅ **Proactive agent** - Agent can suggest: "Should I send John his upload link?"  
✅ **Error handling** - Agent handles invalid emails, expired tokens  
✅ **Personalization** - Custom messages per client  

---

## Security Considerations

✅ **Token security** - 32-byte URL-safe random tokens  
✅ **Time-limited** - Tokens expire after 30 days  
✅ **One-time use** - Token invalidated after first upload (optional)  
✅ **Audit logging** - All token generation logged  
✅ **Email verification** - SES validates recipient emails  
✅ **HTTPS only** - Upload portal requires HTTPS  
✅ **No PII in URL** - Only client_id and token in URL  

---

## Cost Impact

**Additional costs:**
- Lambda invocations: ~$0.0000002 per request
- SES emails: $0.10 per 1,000 emails
- DynamoDB writes: Minimal (already provisioned)

**For 50 clients/season:**
- Lambda: $0.00001
- SES: $0.005
- **Total: ~$0.01 per season**

Negligible cost increase!

---

## Next Steps

1. **Review this plan** - Get approval from team
2. **Implement Phase 1** - Backend Lambda + Gateway tool
3. **Test thoroughly** - Ensure email delivery works
4. **Deploy to production** - Update agent
5. **Monitor usage** - Track adoption and errors
6. **Iterate** - Add features based on feedback

---

**Estimated Total Time:** 4-6 hours for full implementation

**Priority:** High - Completes the automation loop

**Complexity:** Low - Follows existing patterns
