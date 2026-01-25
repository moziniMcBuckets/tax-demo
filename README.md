# Tax Document Collection Agent

An intelligent AI agent built on Amazon Bedrock AgentCore that automates tax document collection for accounting firms. This production-ready solution reduces manual follow-up time by 90% while ensuring clients submit required documents on time.


## What It Does

The Tax Document Collection Agent helps accountants manage client document collection during tax season by:

- **Tracking document status** across all clients in real-time
- **Sending automated reminders** at strategic intervals (Day 3, 10, 24)
- **Providing secure upload portals** with unique tokens per client
- **Escalating urgent cases** automatically based on deadlines
- **Answering questions** about client status via natural language chat
- **Managing requirements** for different tax scenarios (W-2, 1099, business, etc.)

### Key Features

✅ **Multi-channel interface**: Chat with the agent, view dashboard, or use client upload portal  
✅ **Intelligent automation**: Automatic reminders and escalations based on deadlines  
✅ **Secure document handling**: S3 storage with pre-signed URLs and token-based access  
✅ **Email integration**: SES-powered notifications with customizable templates  
✅ **Real-time tracking**: DynamoDB-backed status updates and follow-up history  
✅ **Cost-effective**: ~$3.86 per tax season for 50 clients

## Quick Start

Deploy the complete system in 20 minutes:

```bash
# 1. Install dependencies
cd infra-cdk
npm install

# 2. Configure
cp config-tax-agent.yaml config.yaml
# Edit config.yaml with your stack name and email

# 3. Deploy infrastructure
cdk bootstrap  # First time only
cdk deploy --all --require-approval never

# 4. Deploy frontend
cd ..
python3 scripts/deploy-frontend.py

# 5. Verify email for sending
aws ses verify-email-identity --email-address your-email@domain.com

# 6. Create Cognito user and start using!
```

See the [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

## System Overview

The agent provides three interfaces:

### 1. Chat Interface
Natural language conversation with the AI agent:
```
You: "Show me all my clients"
Agent: "I need your accountant ID to retrieve your clients."

You: "acc_test_001"
Agent: "You have 5 clients: 2 complete, 1 at risk, 2 incomplete..."

You: "Send a reminder to Mohamed Mohamud"
Agent: "Reminder sent successfully to mohamed@example.com"
```

### 2. Dashboard View
Visual overview of all clients with status indicators:
- 🟢 Complete (all documents received)
- 🟡 At Risk (deadline approaching, documents missing)
- 🔴 Escalated (urgent attention needed)
- ⚪ Incomplete (normal follow-up)

### 3. Client Upload Portal
Secure, token-based upload interface for clients:
- No login required (token-based access)
- Drag-and-drop document upload
- Real-time status updates
- Mobile-friendly design

## Architecture

The system uses six specialized tools behind AgentCore Gateway:

1. **Document Checker** - Scans for missing documents and calculates risk scores
2. **Email Sender** - Sends customizable reminder emails via SES
3. **Status Tracker** - Provides overview of all clients and their statuses
4. **Escalation Manager** - Flags urgent cases based on deadlines
5. **Requirement Manager** - Manages document requirements per client
6. **Upload Manager** - Generates secure upload tokens and URLs


### Backend Components

**AWS Services:**
- **AgentCore Runtime** - Hosts the Strands-based agent
- **AgentCore Gateway** - Authenticates and routes tool calls
- **AgentCore Memory** - Stores conversation history
- **DynamoDB** - Client data, requirements, follow-ups, settings
- **S3** - Document storage with lifecycle policies
- **SES** - Email delivery
- **Cognito** - Authentication for frontend and API
- **Lambda** - Six tool implementations
- **API Gateway** - REST API for feedback and uploads

**Tech Stack:**
- Python 3.11+ with Strands SDK
- AWS CDK for infrastructure as code
- Docker for agent containerization

### Frontend Components

**Framework:**
- Next.js 14 with React 18
- TypeScript for type safety
- Tailwind CSS + shadcn/ui components
- Amplify Hosting for deployment

**Features:**
- Real-time streaming responses
- Multi-tab interface (Chat, Dashboard, Upload)
- Mobile-responsive design
- OAuth authentication via Cognito

## Use Cases

This solution is ideal for:

- **Accounting firms** managing tax document collection
- **Financial advisors** gathering client information
- **Legal practices** collecting case documents
- **HR departments** onboarding new employees
- **Any business** requiring systematic document collection with follow-ups

## Documentation

Comprehensive guides are available in the `docs/` folder:

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Step-by-step deployment instructions
- **[Onboarding Guide](docs/ONBOARDING.md)** - Get started with your first client
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow
- **[Gateway Integration](docs/GATEWAY.md)** - How tools work with AgentCore Gateway
- **[Memory Integration](docs/MEMORY_INTEGRATION.md)** - Conversation persistence
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

## Testing

Test scripts are provided for validation:

```bash
# Seed test data (5 sample clients)
python3 scripts/seed-tax-test-data.py

# Test all gateway tools
python3 scripts/test-all-gateway-tools.py

# Test the agent directly
python3 scripts/test-tax-agent.py

# Generate upload token for a client
python3 scripts/generate-upload-token.py --client-id client_001
```


## Cost Analysis

Estimated AWS costs for 50 clients during tax season (3 months):

| Service | Usage | Cost |
|---------|-------|------|
| AgentCore Runtime | 500 invocations | $1.50 |
| AgentCore Gateway | 3,000 calls | $0.30 |
| Lambda | 10,000 invocations | $0.20 |
| DynamoDB | 100K reads/writes | $0.25 |
| S3 | 5GB storage + requests | $0.15 |
| SES | 1,000 emails | $0.10 |
| Cognito | 50 MAU | $0.28 |
| Amplify | Hosting | $1.00 |
| CloudWatch | Logs | $0.08 |
| **Total** | | **~$3.86/season** |

*Costs scale linearly with client count. 500 clients ≈ $38.60/season.*

## Architecture Diagram

![Architecture Diagram](docs/architecture-diagram/FAST-architecture-20251201.png)

The system uses Amazon Cognito for authentication in four places:
1. User login to the frontend web application
2. Frontend to AgentCore Runtime communication
3. Agent to AgentCore Gateway tool calls
4. API Gateway REST endpoints

## Customization

The agent behavior can be customized by editing:

**Agent Prompt:**
```python
# patterns/strands-single-agent/tax_document_agent.py
system_prompt = """
Your custom instructions here...
"""
```

**Email Templates:**
Update in DynamoDB `<stack>-settings` table or via the agent.

**Frontend Branding:**
```typescript
// frontend/src/app/layout.tsx
export const metadata = {
  title: "Your Company Name",
  // ... customize colors, logo, etc.
}
```

After changes, redeploy:
```bash
cd infra-cdk
cdk deploy tax-agent  # For agent changes
cd ..
python3 scripts/deploy-frontend.py  # For frontend changes
```

## Project Structure

```
tax-demo/
├── frontend/                 # Next.js React frontend
│   ├── src/
│   │   ├── app/            # Pages (chat, dashboard, upload)
│   │   ├── components/     # React components
│   │   │   ├── chat/       # Chat interface components
│   │   │   ├── tax/        # Tax-specific components
│   │   │   └── ui/         # shadcn/ui components
│   │   ├── services/       # API integrations
│   │   └── types/          # TypeScript definitions
│   └── package.json
├── infra-cdk/               # AWS CDK infrastructure
│   ├── lib/
│   │   ├── tax-agent-main-stack.ts      # Main orchestration
│   │   ├── tax-agent-backend-stack.ts   # Backend resources
│   │   ├── cognito-stack.ts             # Authentication
│   │   └── amplify-hosting-stack.ts     # Frontend hosting
│   ├── config-tax-agent.yaml            # Tax agent configuration
│   └── package.json
├── patterns/               # Agent implementations
│   └── strands-single-agent/
│       ├── tax_document_agent.py        # Main agent logic
│       ├── basic_agent.py               # Simple chat agent
│       ├── requirements.txt
│       └── Dockerfile
├── gateway/                # AgentCore Gateway tools
│   ├── tools/
│   │   ├── document_checker/            # Missing doc scanner
│   │   ├── email_sender/                # SES email integration
│   │   ├── status_tracker/              # Client overview
│   │   ├── escalation_manager/          # Urgent case flagging
│   │   ├── requirement_manager/         # Doc requirements
│   │   └── upload_manager/              # Secure upload tokens
│   └── layers/common/                   # Shared utilities
├── scripts/                # Deployment and testing
│   ├── deploy-frontend.py               # Frontend deployment
│   ├── seed-tax-test-data.py           # Test data generator
│   ├── test-all-gateway-tools.py       # Tool validation
│   ├── test-tax-agent.py               # Agent testing
│   └── generate-upload-token.py        # Token generator
├── docs/                   # Documentation
│   ├── DEPLOYMENT.md                    # Deployment guide
│   ├── ONBOARDING.md                    # Getting started
│   ├── ARCHITECTURE.md                  # System design
│   ├── GATEWAY.md                       # Gateway integration
│   ├── TROUBLESHOOTING.md              # Common issues
│   └── architecture-diagram/
├── tests/                  # Test suite
│   ├── unit/
│   └── integration/
└── README.md
```

## Prerequisites

- **Node.js 20+** - Frontend and CDK
- **Python 3.11+** - Agent and scripts
- **Docker** - Agent containerization
- **AWS CLI v2** - AWS operations
- **AWS CDK** - Infrastructure deployment
- **AWS Account** - With admin permissions

## Contributing

This is a fork of the [FAST template](https://github.com/awslabs/fullstack-solution-template-for-agentcore). Contributions should follow the patterns established in the original template.

### Development Workflow

1. Make changes to agent, tools, or frontend
2. Test locally using provided scripts
3. Run linting: `make all` (from root)
4. Deploy to test environment
5. Validate changes
6. Commit with conventional commits format

See `vibe-context/` folder for AI coding assistant guidelines.

## Support

For issues specific to this tax demo:
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Review CloudWatch logs
- Test individual components with provided scripts

For FAST template issues:
- See [upstream repository](https://github.com/awslabs/fullstack-solution-template-for-agentcore)

## Roadmap

Planned enhancements:
- [ ] Multi-language support
- [ ] SMS reminders via SNS
- [ ] Advanced analytics dashboard
- [ ] Bulk client import
- [ ] Custom workflow builder
- [ ] Integration with tax software APIs

## Security & Compliance

This solution implements AWS security best practices:
- Encryption at rest (DynamoDB, S3)
- Encryption in transit (TLS)
- IAM least privilege access
- Cognito authentication
- VPC isolation (optional)
- CloudWatch audit logging

**Important:** This is a proof-of-value implementation. For production use, conduct a security review and implement additional controls based on your specific compliance requirements (HIPAA, SOC 2, etc.).

## License

This project is licensed under the Apache-2.0 License.
