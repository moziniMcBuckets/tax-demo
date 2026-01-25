# Tax Document Collection Agent - Implementation Plan

## Problem Statement

Accountants spend 5-10 hours/week during tax season chasing clients for missing documents. This agent automates document tracking, sends personalized follow-ups, and escalates unresponsive cases.

**Value Proposition:** Save 8 hours/week × $75/hr = $600/week for 50-client practice during tax season (Jan-Apr)

---

## Architecture Overview

### Agent Type
**Strands Single Agent** - Perfect for this use case because:
- Tool-heavy workflow (document checking, email sending, status tracking)
- Conversational interface for accountant to query status
- Memory integration to track client interactions over time
- Streaming for real-time status updates

### Core Components

1. **Strands Agent** (`patterns/strands-single-agent/`)
   - Monitors client document status
   - Generates personalized follow-up emails
   - Tracks escalation timelines
   - Provides status reports to accountant

2. **Gateway Tools** (Lambda functions)
   - Document storage scanner (S3/SharePoint/Dropbox)
   - Email sender (SES)
   - Client database manager (DynamoDB)
   - Status tracker and reporter

3. **Frontend** (React/Next.js)
   - Dashboard showing all client statuses
   - Manual override controls
   - Email template editor
   - Escalation queue viewer

4. **Data Storage**
   - DynamoDB: Client records, document requirements, follow-up history
   - S3: Client document folders
   - AgentCore Memory: Conversation history with accountant

---

## Data Model

### DynamoDB Tables

#### 1. Clients Table
```
PK: client_id (UUID)
SK: tax_year (2024)

Attributes:
- client_name: "John Smith"
- email: "john@example.com"
- phone: "+1-555-0123"
- accountant_id: "acc_123"
- status: "incomplete" | "complete" | "at_risk" | "escalated"
- created_at: timestamp
- updated_at: timestamp
```

#### 2. DocumentRequirements Table
```
PK: client_id
SK: document_type (W2, 1099-INT, 1099-DIV, etc.)

Attributes:
- document_type: "W-2"
- source: "Employer XYZ" (optional)
- required: true/false
- received: true/false
- received_date: timestamp
- file_path: "s3://bucket/client_id/w2.pdf"
- last_checked: timestamp
```

#### 3. FollowUpHistory Table
```
PK: client_id
SK: followup_id (timestamp-based)

Attributes:
- followup_number: 1, 2, 3, etc.
- sent_date: timestamp
- email_subject: "Reminder: W-2 needed for tax filing"
- email_body: full text
- documents_requested: ["W-2", "1099-INT"]
- response_received: true/false
- response_date: timestamp
- next_followup_date: timestamp
- escalation_triggered: true/false
```

#### 4. AccountantSettings Table
```
PK: accountant_id
SK: "settings"

Attributes:
- followup_schedule: [3, 7, 14] (days between reminders)
- escalation_threshold: 3 (number of reminders before escalation)
- escalation_days: 48 (hours before escalation)
- email_templates: {
    "reminder_1": "template text",
    "reminder_2": "template text",
    "reminder_3": "template text",
    "escalation": "template text"
  }
- business_hours: "9am-5pm EST"
- tax_season_start: "2025-01-15"
- tax_season_end: "2025-04-15"
```

---

## Gateway Tools Design

### Tool 1: check_client_documents
**Purpose:** Scan client folder and compare against required documents

**Lambda:** `gateway/tools/document_checker/document_checker_lambda.py`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "description": "Unique client identifier"
    },
    "tax_year": {
      "type": "integer",
      "description": "Tax year (e.g., 2024)"
    }
  },
  "required": ["client_id", "tax_year"]
}
```

**Output:**
```json
{
  "client_name": "John Smith",
  "status": "incomplete",
  "required_documents": [
    {
      "type": "W-2",
      "source": "Employer ABC",
      "received": false,
      "last_checked": "2025-01-20T10:30:00Z"
    },
    {
      "type": "1099-INT",
      "source": "Chase Bank",
      "received": false,
      "last_checked": "2025-01-20T10:30:00Z"
    }
  ],
  "received_documents": [
    {
      "type": "1099-DIV",
      "source": "Vanguard",
      "received_date": "2025-01-15T14:20:00Z",
      "file_path": "s3://bucket/client_123/1099-div.pdf"
    }
  ],
  "completion_percentage": 33
}
```

**Implementation:**
- Query DynamoDB DocumentRequirements table
- Scan S3 bucket for client folder
- Use document classification (Bedrock or pattern matching) to identify document types
- Update DynamoDB with findings
- Return structured status

---

### Tool 2: send_followup_email
**Purpose:** Send personalized follow-up email to client

**Lambda:** `gateway/tools/email_sender/email_sender_lambda.py`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "description": "Unique client identifier"
    },
    "missing_documents": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of missing document types"
    },
    "followup_number": {
      "type": "integer",
      "description": "Which reminder this is (1, 2, 3, etc.)"
    },
    "custom_message": {
      "type": "string",
      "description": "Optional custom message to include"
    }
  },
  "required": ["client_id", "missing_documents", "followup_number"]
}
```

**Output:**
```json
{
  "success": true,
  "email_sent": true,
  "recipient": "john@example.com",
  "subject": "Reminder #2: Documents needed for your 2024 tax return",
  "sent_at": "2025-01-20T10:35:00Z",
  "followup_id": "fu_abc123",
  "next_followup_date": "2025-01-27T10:35:00Z"
}
```

**Implementation:**
- Fetch client email from DynamoDB
- Fetch accountant's email template settings
- Generate personalized email using template + missing docs
- Send via AWS SES
- Log to FollowUpHistory table
- Calculate next follow-up date based on schedule
- Return confirmation

---

### Tool 3: get_client_status
**Purpose:** Get comprehensive status for one or all clients

**Lambda:** `gateway/tools/status_tracker/status_tracker_lambda.py`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "description": "Specific client ID, or 'all' for all clients"
    },
    "filter": {
      "type": "string",
      "enum": ["all", "incomplete", "at_risk", "escalated", "complete"],
      "description": "Filter by status"
    },
    "accountant_id": {
      "type": "string",
      "description": "Accountant ID to filter clients"
    }
  },
  "required": ["accountant_id"]
}
```

**Output:**
```json
{
  "summary": {
    "total_clients": 50,
    "complete": 15,
    "incomplete": 25,
    "at_risk": 8,
    "escalated": 2
  },
  "clients": [
    {
      "client_id": "client_123",
      "client_name": "John Smith",
      "status": "at_risk",
      "completion_percentage": 33,
      "missing_documents": ["W-2", "1099-INT"],
      "last_followup": "2025-01-15T10:00:00Z",
      "followup_count": 2,
      "days_until_escalation": 2,
      "next_action": "Send reminder #3 on 2025-01-22"
    }
  ]
}
```

**Implementation:**
- Query DynamoDB Clients table (with GSI on accountant_id)
- Join with DocumentRequirements to calculate completion
- Join with FollowUpHistory to get last contact
- Calculate risk status based on follow-up schedule
- Return aggregated data

---

### Tool 4: escalate_client
**Purpose:** Mark client for accountant intervention

**Lambda:** `gateway/tools/escalation_manager/escalation_manager_lambda.py`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "description": "Client to escalate"
    },
    "reason": {
      "type": "string",
      "description": "Reason for escalation"
    },
    "notify_accountant": {
      "type": "boolean",
      "description": "Send notification to accountant"
    }
  },
  "required": ["client_id", "reason"]
}
```

**Output:**
```json
{
  "success": true,
  "client_id": "client_123",
  "escalated_at": "2025-01-20T10:40:00Z",
  "accountant_notified": true,
  "escalation_reason": "No response after 3 reminders over 14 days"
}
```

**Implementation:**
- Update client status to "escalated" in DynamoDB
- Log escalation event
- Optionally send email/SMS to accountant
- Return confirmation

---

### Tool 5: update_document_requirements
**Purpose:** Add/modify required documents for a client

**Lambda:** `gateway/tools/requirement_manager/requirement_manager_lambda.py`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "client_id": {
      "type": "string",
      "description": "Client identifier"
    },
    "tax_year": {
      "type": "integer",
      "description": "Tax year"
    },
    "documents": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "document_type": {"type": "string"},
          "source": {"type": "string"},
          "required": {"type": "boolean"}
        }
      },
      "description": "List of required documents"
    }
  },
  "required": ["client_id", "tax_year", "documents"]
}
```

**Output:**
```json
{
  "success": true,
  "client_id": "client_123",
  "documents_updated": 5,
  "updated_at": "2025-01-20T10:45:00Z"
}
```

---

## Strands Agent Implementation

### System Prompt

```python
system_prompt = """You are a Tax Document Collection Assistant for accountants.

Your role is to help accountants track client document submissions during tax season and automate follow-up communications.

**Your capabilities:**
1. Check which clients have submitted required documents
2. Identify missing documents for each client
3. Send personalized follow-up emails to clients
4. Track follow-up history and response rates
5. Escalate unresponsive clients to the accountant
6. Provide status reports and analytics

**Document types you track:**
- W-2 (wage and tax statement)
- 1099-INT (interest income)
- 1099-DIV (dividend income)
- 1099-MISC (miscellaneous income)
- 1099-NEC (non-employee compensation)
- 1099-B (broker transactions)
- 1099-R (retirement distributions)
- Receipts for deductions
- Prior year tax returns
- Other tax-related documents

**Follow-up protocol:**
- Reminder 1: Sent 3 days after initial request
- Reminder 2: Sent 7 days after Reminder 1
- Reminder 3: Sent 14 days after Reminder 2
- Escalation: Flag for accountant call if no response 48 hours after Reminder 3

**Status categories:**
- Complete: All required documents received
- Incomplete: Some documents missing, follow-ups in progress
- At Risk: Multiple reminders sent, approaching escalation
- Escalated: Requires accountant intervention

**Communication style:**
- Professional but friendly
- Specific about what's needed
- Include deadlines when relevant
- Personalize based on client name and specific missing items

**When interacting with the accountant:**
- Provide clear, actionable summaries
- Highlight urgent cases first
- Suggest next steps
- Be concise but thorough

Always use your tools to check current status before making recommendations.
"""
```

### Agent Configuration

**File:** `patterns/strands-single-agent/tax_document_agent.py`

```python
# Key modifications to basic_agent.py:

# 1. Update system prompt (above)
# 2. Add Gateway tools for document checking, email sending, status tracking
# 3. Configure memory to track client interactions
# 4. Add scheduled invocation support (EventBridge trigger)

# Model configuration
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    temperature=0.1  # Low temperature for consistent, factual responses
)

# Tools from Gateway
tools = [
    gateway_client,  # Provides all 5 tools above
]

# Agent with memory
agent = Agent(
    name="TaxDocumentAgent",
    system_prompt=system_prompt,
    tools=tools,
    model=bedrock_model,
    session_manager=session_manager,
    trace_attributes={
        "accountant.id": accountant_id,
        "session.id": session_id,
    },
)
```

---

## Frontend Design

### Dashboard Components

#### 1. Client Status Dashboard
**File:** `frontend/src/components/tax/ClientDashboard.tsx`

**Features:**
- Table view of all clients with status indicators
- Color coding: Green (complete), Yellow (incomplete), Orange (at risk), Red (escalated)
- Sortable columns: Name, Status, Completion %, Last Contact, Days Until Escalation
- Quick filters: Show All, Incomplete Only, At Risk, Escalated
- Search by client name

#### 2. Client Detail View
**File:** `frontend/src/components/tax/ClientDetail.tsx`

**Features:**
- Client information header
- Document checklist with received/missing indicators
- Follow-up history timeline
- Manual actions: Send Custom Email, Mark Document Received, Escalate Now
- Notes section for accountant comments

#### 3. Email Template Editor
**File:** `frontend/src/components/tax/EmailTemplateEditor.tsx`

**Features:**
- Edit templates for Reminder 1, 2, 3, and Escalation
- Variable insertion: {client_name}, {missing_documents}, {deadline}
- Preview with sample data
- Save/Reset buttons

#### 4. Chat Interface (existing)
**File:** `frontend/src/components/chat/ChatInterface.tsx`

**Enhancements:**
- Quick commands: "/status", "/check [client]", "/remind [client]"
- Display client status cards in chat
- Action buttons in chat responses

---

## Scheduled Automation

### EventBridge Rules

**Daily Check (9 AM):**
```
Rule: tax-document-daily-check
Schedule: cron(0 9 * * ? *)
Target: AgentCore Runtime
Payload: {
  "action": "daily_check",
  "accountant_id": "acc_123"
}
```

**Agent Action:**
1. Check all clients for missing documents
2. Identify clients due for follow-up
3. Send scheduled reminder emails
4. Flag clients for escalation
5. Send summary report to accountant

---

## User Workflows

### Workflow 1: Accountant Checks Status
```
Accountant: "Show me the status of all my clients"

Agent: 
- Calls get_client_status tool
- Displays summary: "You have 50 clients. 15 complete, 25 incomplete, 8 at risk, 2 escalated"
- Shows table with at-risk clients highlighted
- Suggests: "Would you like me to send reminders to the 8 at-risk clients?"
```

### Workflow 2: Automated Daily Check
```
EventBridge triggers agent at 9 AM

Agent:
1. Calls get_client_status for all clients
2. For each client due for follow-up:
   - Calls check_client_documents
   - Calls send_followup_email with missing docs
3. For clients past escalation threshold:
   - Calls escalate_client
4. Sends summary email to accountant:
   "Daily Report: 5 reminders sent, 2 clients escalated, 3 new documents received"
```

### Workflow 3: Accountant Asks About Specific Client
```
Accountant: "What's the status of John Smith?"

Agent:
- Calls check_client_documents(client_id="john_smith")
- Responds: "John Smith is at risk. Missing: W-2 from Employer ABC, 1099-INT from Chase Bank. 
  Last reminder sent 5 days ago (Reminder #2). No response yet. 
  Next reminder scheduled for tomorrow. Will escalate in 2 days if no response."
- Suggests: "Would you like me to send Reminder #3 now, or would you prefer to call him directly?"
```

### Workflow 4: Manual Override
```
Accountant: "John Smith just emailed me his W-2. Mark it as received."

Agent:
- Calls update_document_requirements to mark W-2 as received
- Calls check_client_documents to get updated status
- Responds: "Updated! John Smith now has 1 of 2 documents. Still missing: 1099-INT from Chase Bank. 
  Status changed from 'at risk' to 'incomplete'. Should I send a reminder about the 1099-INT?"
```

---

## Configuration & Deployment

### 1. Update `infra-cdk/config.yaml`
```yaml
stack_name_base: tax-document-agent
admin_user_email: accountant@example.com
backend:
  pattern: strands-single-agent
  deployment_type: docker
```

### 2. Environment Variables
Add to `infra-cdk/lib/backend-stack.ts`:
```typescript
EnvironmentVariables: {
  MEMORY_ID: memoryResource.attrMemoryId,
  STACK_NAME: config.stack_name_base,
  CLIENTS_TABLE: clientsTable.tableName,
  DOCUMENTS_TABLE: documentsTable.tableName,
  FOLLOWUP_TABLE: followupTable.tableName,
  SETTINGS_TABLE: settingsTable.tableName,
  CLIENT_BUCKET: clientBucket.bucketName,
  SES_FROM_EMAIL: "noreply@yourdomain.com",
  AWS_DEFAULT_REGION: this.region,
}
```

### 3. IAM Permissions
Grant to Gateway Lambda roles:
- DynamoDB: Read/Write on all tables
- S3: Read on client bucket
- SES: SendEmail permission
- Secrets Manager: Read email credentials (if using external email)

### 4. DynamoDB Table Creation
Add to `infra-cdk/lib/backend-stack.ts`:
```typescript
// Create all 4 DynamoDB tables with appropriate GSIs
// GSI on Clients table: accountant_id for filtering
// GSI on FollowUpHistory: client_id + sent_date for timeline queries
```

### 5. S3 Bucket Setup
```typescript
const clientBucket = new s3.Bucket(this, 'ClientDocuments', {
  bucketName: `${config.stack_name_base}-client-docs`,
  encryption: s3.BucketEncryption.S3_MANAGED,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  versioned: true,
  lifecycleRules: [
    {
      expiration: cdk.Duration.days(2555), // 7 years for tax records
    }
  ]
});
```

### 6. SES Configuration
- Verify sender email domain
- Move out of SES sandbox for production
- Set up DKIM/SPF records
- Configure bounce/complaint handling

---

## Testing Strategy

### Unit Tests
**File:** `tests/unit/test_document_checker.py`
- Test document type classification
- Test S3 scanning logic
- Test DynamoDB queries

**File:** `tests/unit/test_email_sender.py`
- Test email template rendering
- Test personalization logic
- Mock SES calls

### Integration Tests
**File:** `tests/integration/test_agent_workflow.py`
- Test full check → remind → escalate flow
- Test scheduled automation
- Test manual overrides

### Manual Testing
**File:** `scripts/test-tax-agent.py`
- Create test clients with mock data
- Trigger agent with various queries
- Verify tool calls and responses
- Check DynamoDB updates

---

## Security Considerations

### Data Protection
- **PII Handling:** Client names, emails, SSNs in documents
- **Encryption:** At rest (S3, DynamoDB) and in transit (TLS)
- **Access Control:** IAM policies, Cognito user pools
- **Audit Logging:** CloudWatch logs for all actions

### Compliance
- **Tax Data Retention:** 7-year retention policy
- **GDPR/Privacy:** Client consent for automated emails
- **Email Compliance:** CAN-SPAM Act compliance (unsubscribe links)
- **Data Breach:** Incident response plan

### Rate Limiting
- **Email Sending:** Respect SES limits (14 emails/sec in sandbox)
- **API Calls:** Throttle DynamoDB/S3 operations
- **Cost Controls:** Set billing alarms

---

## Pricing Estimate

### AWS Costs (50 clients, 4-month tax season)

**AgentCore Runtime:**
- $0.00025 per request
- ~500 requests/day (daily checks + accountant queries)
- 120 days × 500 = 60,000 requests
- Cost: $15

**Lambda (Gateway Tools):**
- ~1,000 invocations/day
- 120 days × 1,000 = 120,000 invocations
- Cost: ~$2 (within free tier)

**DynamoDB:**
- On-demand pricing
- ~10,000 read/write units per day
- Cost: ~$15/month × 4 = $60

**S3:**
- 50 clients × 10 documents × 1 MB = 500 MB
- Cost: ~$0.01/month

**SES:**
- 50 clients × 3 reminders × 4 months = 600 emails
- Cost: $0.06 (within free tier)

**Total AWS Cost:** ~$100 for 4-month tax season

**Agent Pricing:** $500-1,000/month = $2,000-4,000 for tax season
**Margin:** 95%+ after AWS costs

---

## Development Timeline

### Phase 1: Foundation (Week 1)
- Set up DynamoDB tables
- Create S3 bucket structure
- Implement document_checker tool
- Test document scanning

### Phase 2: Core Agent (Week 2)
- Update Strands agent with tax-specific prompt
- Integrate document_checker tool
- Implement status_tracker tool
- Test agent queries

### Phase 3: Email Automation (Week 3)
- Implement email_sender tool
- Set up SES and templates
- Test email generation and sending
- Implement followup_history tracking

### Phase 4: Escalation & Scheduling (Week 4)
- Implement escalation_manager tool
- Set up EventBridge rules
- Test automated daily checks
- Implement requirement_manager tool

### Phase 5: Frontend (Week 5-6)
- Build client dashboard
- Create client detail view
- Add email template editor
- Integrate with chat interface

### Phase 6: Testing & Polish (Week 7-8)
- End-to-end testing with real data
- Performance optimization
- Security audit
- Documentation

**Total:** 8 weeks to production-ready

---

## Success Metrics

### Operational Metrics
- **Time Saved:** Hours per week saved by accountant
- **Response Rate:** % of clients responding to automated emails
- **Completion Rate:** % of clients submitting all documents on time
- **Escalation Rate:** % of clients requiring manual intervention

### Technical Metrics
- **Agent Accuracy:** % of correct document classifications
- **Email Delivery Rate:** % of emails successfully delivered
- **System Uptime:** % availability during tax season
- **Response Time:** Average time for agent queries

### Business Metrics
- **ROI:** Time saved × billing rate vs. agent cost
- **Client Satisfaction:** Feedback on automated communications
- **Deadline Compliance:** % of returns filed on time
- **Accountant Adoption:** % of accountants using the system regularly

---

## Future Enhancements

### Phase 2 Features
1. **SMS Reminders:** Add Twilio integration for text messages
2. **Document Upload Portal:** Client-facing web portal for uploads
3. **OCR & Validation:** Automatically extract data from uploaded documents
4. **Multi-Accountant Support:** Firm-wide deployment with role-based access
5. **Analytics Dashboard:** Trends, benchmarks, year-over-year comparisons
6. **Mobile App:** iOS/Android app for accountants
7. **Integration:** QuickBooks, TaxDome, Drake Tax Software
8. **AI Document Review:** Flag potential issues in submitted documents

### Advanced Features
- **Predictive Analytics:** Predict which clients will be late
- **Smart Scheduling:** Optimize follow-up timing based on client behavior
- **Batch Operations:** Bulk actions across multiple clients
- **Custom Workflows:** Accountant-defined automation rules
- **Multi-Language:** Support for non-English clients

---

## Risk Mitigation

### Technical Risks
- **Email Deliverability:** Use authenticated domain, monitor bounce rates
- **Document Classification Errors:** Human review for ambiguous cases
- **System Downtime:** Multi-AZ deployment, automated failover
- **Data Loss:** Regular backups, versioning enabled

### Business Risks
- **Client Pushback:** Clear opt-in, professional communication
- **Accountant Adoption:** Training, support, gradual rollout
- **Regulatory Changes:** Stay updated on tax law changes
- **Competition:** Continuous feature development

---

## Conclusion

This implementation plan leverages FAST's strengths:
- **Gateway architecture** for scalable, independent tools
- **Strands framework** for tool-heavy workflows
- **Memory integration** for tracking client interactions
- **Streaming** for real-time status updates
- **Existing auth** for secure multi-user access

The agent solves a real pain point with clear ROI, making it an excellent candidate for a production SaaS offering.

**Next Steps:**
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Iterate based on feedback

