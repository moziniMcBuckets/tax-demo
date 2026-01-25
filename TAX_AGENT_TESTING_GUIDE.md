# Tax Document Agent - Testing Guide

## Overview

This guide covers testing the tax document collection agent at multiple levels:
- Unit tests for Lambda functions
- Integration tests for Gateway tools
- End-to-end tests for the complete agent
- Performance and cost monitoring

---

## Test Scripts Created

### 1. Seed Test Data ✅
**File:** `scripts/seed-tax-test-data.py`

**What it does:**
- Creates 5 sample clients with different statuses
- Adds document requirements for each client
- Creates follow-up history
- Sets up accountant settings

**Usage:**
```bash
python scripts/seed-tax-test-data.py
```

**Output:**
- 5 clients created (complete, incomplete, at_risk, escalated)
- Document requirements for each
- Follow-up history (1-3 reminders per client)
- Accountant preferences and contact info

### 2. Test Gateway Tools ✅
**File:** `scripts/test-tax-gateway.py`

**What it does:**
- Authenticates with Cognito (OAuth2)
- Lists all available Gateway tools
- Tests each tool individually:
  - check_client_documents
  - get_client_status
  - update_document_requirements

**Usage:**
```bash
python scripts/test-tax-gateway.py
```

**Expected Output:**
```
✓ Access token obtained
✓ Found 5 tools
✓ check_client_documents: Success
✓ get_client_status: Success
✓ update_document_requirements: Success
```

### 3. Test Agent End-to-End ✅
**File:** `scripts/test-tax-agent.py`

**What it does:**
- Invokes AgentCore Runtime directly
- Tests multiple query types
- Verifies memory persistence
- Checks tool usage

**Usage:**
```bash
python scripts/test-tax-agent.py
```

**Test Queries:**
1. "Show me the status of all my clients"
2. "What documents are missing for John Smith?"
3. "Which clients are at risk?"
4. "What tools do you have access to?"
5. "What did I ask you about in my first question?" (memory test)

---

## Testing Workflow

### Step 1: Deploy Infrastructure

```bash
cd infra-cdk
npm install
cdk bootstrap  # First time only
cdk deploy --all
```

### Step 2: Seed Test Data

```bash
cd ..
python scripts/seed-tax-test-data.py
```

**Verify:**
```bash
# Check DynamoDB tables
aws dynamodb scan --table-name tax-agent-clients --max-items 5

# Expected: 5 clients
```

### Step 3: Test Gateway Tools

```bash
python scripts/test-tax-gateway.py
```

**Verify:**
- All 5 tools listed
- Tool calls return valid JSON
- No authentication errors
- Response times < 5 seconds

### Step 4: Test Agent

```bash
python scripts/test-tax-agent.py
```

**Verify:**
- Agent responds to all queries
- Tools are called appropriately
- Memory persists across turns
- Responses are relevant and accurate

### Step 5: Test Frontend

```bash
# Deploy frontend
python scripts/deploy-frontend.py

# Open in browser
# Test login and chat interface
```

---

## Manual Testing Scenarios

### Scenario 1: New Client Onboarding

**Steps:**
1. Add new client via frontend or DynamoDB
2. Apply standard requirements
3. Ask agent: "What documents does [client] need?"
4. Verify agent lists all requirements

**Expected:**
- Agent calls `check_client_documents`
- Returns list of required documents
- Shows 0% completion

### Scenario 2: Document Upload

**Steps:**
1. Upload document to S3: `s3://bucket/client_id/2024/w2.pdf`
2. Add metadata: `document-type: W-2`
3. Ask agent: "Check status for [client]"
4. Verify agent detects new document

**Expected:**
- Agent calls `check_client_documents`
- Detects uploaded W-2
- Updates completion percentage
- Lists remaining missing documents

### Scenario 3: Send Reminder

**Steps:**
1. Ask agent: "Send a reminder to [client]"
2. Verify email sent (check SES console)
3. Check follow-up history in DynamoDB

**Expected:**
- Agent calls `check_client_documents` first
- Then calls `send_followup_email`
- Email sent via SES
- Follow-up logged in DynamoDB
- Next reminder scheduled

### Scenario 4: Escalation

**Steps:**
1. Ask agent: "Escalate [client]"
2. Check accountant email
3. Verify client status updated

**Expected:**
- Agent calls `escalate_client`
- Email sent to accountant
- SNS notification published
- Client status = 'escalated'
- Escalation logged

### Scenario 5: Multi-Turn Conversation

**Steps:**
1. Ask: "Show me all clients"
2. Ask: "Tell me more about the at-risk ones"
3. Ask: "Send reminders to them"

**Expected:**
- Agent uses memory from previous turns
- Doesn't re-query for client list
- Sends reminders to correct clients
- Maintains context throughout

---

## Performance Testing

### Load Test

```bash
# Test concurrent requests
for i in {1..10}; do
  python scripts/test-tax-agent.py &
done
wait

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=tax-agent-document-checker \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

### Response Time Test

```bash
# Measure agent response time
time python scripts/test-tax-agent.py

# Expected: 5-15 seconds per query
```

---

## Cost Monitoring

### Check Actual Costs

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

### View Cost Dashboard

```bash
# Open CloudWatch dashboard
aws cloudwatch get-dashboard --dashboard-name tax-agent-costs
```

Or visit: AWS Console → CloudWatch → Dashboards → `tax-agent-costs`

---

## Troubleshooting Tests

### Issue: "No test clients found"

**Solution:**
```bash
# Run seed script first
python scripts/seed-tax-test-data.py
```

### Issue: "Access token failed"

**Solution:**
```bash
# Verify machine client credentials
aws ssm get-parameter --name /tax-agent/machine_client_id

# Check Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id /tax-agent/machine_client_secret
```

### Issue: "Gateway not found"

**Solution:**
```bash
# Verify Gateway deployed
aws bedrock-agentcore list-gateways

# Check SSM parameter
aws ssm get-parameter --name /tax-agent/gateway_url
```

### Issue: "Runtime not responding"

**Solution:**
```bash
# Check Runtime logs
aws logs tail /aws/bedrock-agentcore/runtime/tax_agent_TaxAgent --follow

# Check Runtime status
aws bedrock-agentcore describe-runtime --runtime-identifier <arn>
```

---

## Validation Checklist

### Gateway Tools:
- [ ] All 5 tools listed in tools/list
- [ ] check_client_documents returns valid JSON
- [ ] send_followup_email logs to DynamoDB
- [ ] get_client_status aggregates correctly
- [ ] escalate_client sends notifications
- [ ] update_document_requirements modifies DynamoDB

### Agent:
- [ ] Agent responds to queries
- [ ] Agent calls appropriate tools
- [ ] Agent provides relevant answers
- [ ] Memory persists across turns
- [ ] Streaming works correctly
- [ ] Error handling works

### Infrastructure:
- [ ] DynamoDB tables created
- [ ] S3 bucket created
- [ ] Lambda functions deployed
- [ ] Gateway accessible
- [ ] Runtime running
- [ ] Memory configured

### Cost:
- [ ] DynamoDB using provisioned capacity
- [ ] Lambda using ARM64
- [ ] Logs retention set to 1 month
- [ ] Cost alarm configured
- [ ] Dashboard showing metrics

---

## Success Criteria

### Gateway Tools:
✅ All tools respond within 5 seconds
✅ No authentication errors
✅ Valid JSON responses
✅ DynamoDB updates successful
✅ S3 reads successful

### Agent:
✅ Responds to all test queries
✅ Uses tools appropriately
✅ Provides accurate information
✅ Memory works across turns
✅ Streaming delivers tokens

### Performance:
✅ Response time < 15 seconds
✅ No timeout errors
✅ No memory errors
✅ Cost within budget

---

## Next Steps After Testing

### If Tests Pass:
1. ✅ Deploy to production
2. ✅ Add real clients
3. ✅ Customize email templates
4. ✅ Monitor costs
5. ✅ Scale as needed

### If Tests Fail:
1. Check CloudWatch logs
2. Verify IAM permissions
3. Check DynamoDB data
4. Test tools individually
5. Review error messages

---

## Continuous Testing

### Daily:
- Monitor CloudWatch dashboard
- Check cost metrics
- Review error logs

### Weekly:
- Run test scripts
- Verify automation working
- Check escalation notifications

### Monthly:
- Performance review
- Cost analysis
- Feature improvements

---

**Testing Guide Version:** 1.0
**Last Updated:** 2025-01-24
**Status:** Ready for testing
