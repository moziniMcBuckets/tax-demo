# Architecture - Tax Document Agent

## System Overview

The Tax Document Agent is built on AWS Bedrock AgentCore using the FAST (Fullstack AgentCore Solution Template) framework.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                     │
│  ┌─────────┐  ┌───────────┐  ┌──────────────┐          │
│  │  Chat   │  │ Dashboard │  │Upload Portal │          │
│  └─────────┘  └───────────┘  └──────────────┘          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS + OAuth
┌────────────────────┴────────────────────────────────────┐
│              AgentCore Runtime (Strands)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AI Agent (Claude 3.5 Haiku)                     │   │
│  │  - Tax document expertise                        │   │
│  │  - Conversation memory                           │   │
│  │  - Tool orchestration                            │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────┴────────────────────────────────────┐
│              AgentCore Gateway                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Tool 1   │  │ Tool 2   │  │ Tool 3   │  ...        │
│  └──────────┘  └──────────┘  └──────────┘             │
└────────────────────┬────────────────────────────────────┘
                     │ Lambda Invoke
┌────────────────────┴────────────────────────────────────┐
│           7 Lambda Functions (ARM64)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Doc Checker   │  │Email Sender  │  │Status Tracker│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Escalation Mgr│  │Requirement Mgr│ │Upload Manager│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐                                        │
│  │Doc Processor │                                        │
│  └──────────────┘                                        │
└────────────────────┬────────────────────────────────────┘
                     │ Read/Write
┌────────────────────┴────────────────────────────────────┐
│              Data Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  DynamoDB    │  │      S3      │  │     SES      │  │
│  │  (5 tables)  │  │  (documents) │  │   (emails)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Components

### Frontend (React + Next.js)

**Technology:**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui components

**Features:**
- Chat interface with streaming
- Client dashboard with filters
- Upload portal with progress
- Cognito authentication

**Hosting:** AWS Amplify

### AI Agent (Strands)

**Model:** Claude 3.5 Haiku
- 90% cheaper than Sonnet
- Fast response times
- Good tool-calling accuracy

**Features:**
- Tax document expertise
- 6 Gateway tools
- Conversation memory (120 days)
- Streaming responses

**Hosting:** AgentCore Runtime (Docker, ARM64)

### Gateway Tools (7 Lambda Functions)

**All functions:**
- Runtime: Python 3.13
- Architecture: ARM64 (20% cost savings)
- Memory: 256-512 MB
- Timeout: 30-60 seconds
- Logs: 1-month retention

**Tools:**
1. **Document Checker** - Scans S3, classifies documents
2. **Email Sender** - SES integration, templates
3. **Status Tracker** - Aggregates client data
4. **Escalation Manager** - Notifications
5. **Requirement Manager** - CRUD operations
6. **Upload Manager** - Presigned URLs
7. **Document Processor** - S3 event handler

### Data Layer

**DynamoDB Tables (5):**
1. **Clients** - Client information
   - Key: client_id
   - GSI: accountant-index (accountant_id, status)
   - Billing: Provisioned (1 RCU/WCU)

2. **Documents** - Document requirements
   - Key: client_id, document_type
   - Billing: Provisioned (1 RCU/WCU)

3. **Followups** - Follow-up history
   - Key: client_id, followup_id
   - Billing: Provisioned (1 RCU/WCU)

4. **Settings** - Accountant preferences
   - Key: accountant_id, settings_type
   - Billing: Provisioned (1 RCU/WCU)

5. **Feedback** - User feedback
   - Key: feedbackId
   - Billing: On-demand

**S3 Bucket:**
- Client documents
- Versioning enabled
- Intelligent tiering
- Lifecycle: Glacier (120 days), Deep Archive (365 days)
- Retention: 7 years

### Authentication

**Cognito User Pool:**
- Email-based login
- OAuth2 + JWT
- Machine-to-machine client for Gateway

**Flow:**
1. User logs in → Gets JWT token
2. Frontend calls Runtime with token
3. Runtime validates with Cognito
4. Runtime calls Gateway with OAuth token
5. Gateway validates and routes to Lambda

---

## Data Flow

### Document Upload Flow:

```
1. Accountant generates upload token
   ↓
2. Client receives email with link
   ↓
3. Client opens upload portal
   ↓
4. Portal requests presigned URL (Upload Manager)
   ↓
5. Client uploads directly to S3
   ↓
6. S3 triggers Document Processor Lambda
   ↓
7. Lambda updates DynamoDB (document received)
   ↓
8. Next agent query sees updated status
```

### Reminder Flow:

```
1. Agent checks client status (Document Checker)
   ↓
2. Identifies missing documents
   ↓
3. Calls Email Sender tool
   ↓
4. Email Sender:
   - Gets client email from DynamoDB
   - Personalizes template
   - Sends via SES
   - Logs to DynamoDB
   ↓
5. Client receives email
```

### Escalation Flow:

```
1. Agent detects 3+ reminders with no response
   ↓
2. Calls Escalation Manager tool
   ↓
3. Escalation Manager:
   - Updates client status to "escalated"
   - Sends email to accountant
   - Publishes SNS notification
   - Logs escalation event
   ↓
4. Accountant receives notification
```

---

## Cost Optimization

### Strategies Implemented:

1. **DynamoDB Provisioned Capacity**
   - 96% savings vs on-demand
   - Auto-scaling for bursts

2. **ARM64 Lambda Architecture**
   - 20% savings vs x86
   - All tax tools use ARM64

3. **Claude Haiku Model**
   - 90% cheaper than Sonnet
   - Sufficient for tax use case

4. **Prompt Caching**
   - System prompt > 1,024 tokens
   - 50-70% input token savings

5. **S3 Intelligent Tiering**
   - Automatic cost optimization
   - Glacier for old documents

6. **1-Month Log Retention**
   - 67% savings vs indefinite
   - Sufficient for debugging

**Result:** $3.86/season for 50 clients (vs $85+ without optimization)

---

## Security

### Authentication:
- Cognito User Pool (accountants)
- JWT tokens (short-lived)
- OAuth2 machine-to-machine (Gateway)

### Authorization:
- IAM least-privilege roles
- Resource-level permissions
- No hardcoded credentials

### Data Protection:
- Encryption at rest (DynamoDB, S3)
- Encryption in transit (TLS)
- Presigned URLs (time-limited)
- 7-year retention policy

### Compliance:
- Tax document retention (7 years)
- Audit logging (CloudWatch)
- Access controls (IAM)

---

## Scalability

### Current Capacity:
- 50 clients: $3.86/season
- 500 clients: $72/season
- 5,000 clients: $720/season

### Scaling Considerations:

**At 100+ clients:**
- GSI becomes important
- Consider reserved DynamoDB capacity

**At 500+ clients:**
- Add ElastiCache for caching
- Increase Lambda concurrency
- Monitor DynamoDB throttling

**At 1,000+ clients:**
- Multi-region deployment
- CDN for frontend
- Database sharding

---

## Monitoring

### CloudWatch Dashboard:
- Lambda invocations
- DynamoDB capacity
- Error rates
- Cost metrics

### Alarms:
- Daily cost > $5
- Lambda errors > 10/hour
- DynamoDB throttling

### Logs:
- Lambda: `/aws/lambda/<function-name>`
- Runtime: `/aws/bedrock-agentcore/runtime/*`
- Gateway: `/aws/bedrock-agentcore/gateway/*`

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Next.js | 16.x |
| UI | React | 19.x |
| Styling | Tailwind CSS | 4.x |
| Agent Framework | Strands | 1.16.0 |
| Agent Model | Claude Haiku | 3.5 |
| Runtime | Python | 3.13 |
| Infrastructure | AWS CDK | 2.233.0 |
| Database | DynamoDB | - |
| Storage | S3 | - |
| Auth | Cognito | - |
| Hosting | Amplify | - |

---

## File Structure

```
tax-agent/
├── docs/                    # Documentation
│   ├── TAX_AGENT_README.md
│   ├── DEPLOYMENT.md
│   ├── TROUBLESHOOTING.md
│   ├── ONBOARDING.md
│   └── ARCHITECTURE.md (this file)
├── gateway/
│   ├── tools/              # 7 Lambda tools
│   └── layers/             # Common utilities
├── patterns/
│   └── strands-single-agent/
│       └── tax_document_agent.py
├── frontend/
│   └── src/
│       ├── components/tax/ # Dashboard, Detail, Upload
│       └── app/            # Next.js pages
├── infra-cdk/
│   ├── lib/
│   │   └── backend-stack.ts
│   └── config.yaml
└── scripts/
    ├── seed-tax-test-data.py
    ├── test-all-gateway-tools.py
    └── generate-upload-token.py
```

---

## Design Decisions

### Why Strands?
- Excellent for tool-heavy workflows
- Native MCP support
- Built-in streaming
- Simple API

### Why Haiku?
- 90% cheaper than Sonnet
- Fast enough for this use case
- Good tool-calling accuracy

### Why DynamoDB?
- Serverless (no management)
- Provisioned capacity (cost-effective)
- Fast queries with GSI
- Auto-scaling

### Why Lambda?
- Serverless (no servers to manage)
- Pay per request
- ARM64 cost savings
- Easy to deploy

### Why AgentCore?
- Managed agent runtime
- Built-in memory
- Gateway for tools
- Production-ready

---

## Future Enhancements

### Phase 2:
- SMS reminders (Twilio)
- Document OCR (Textract)
- QuickBooks integration
- Mobile app
- Analytics dashboard

### Phase 3:
- Multi-language support
- AI document review
- Predictive analytics
- Batch operations

---

**Architecture Version:** 1.0
**Last Updated:** January 25, 2026
**Status:** Production
