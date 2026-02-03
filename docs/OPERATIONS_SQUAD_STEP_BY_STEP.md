# Operations Squad: Step-by-Step Implementation

**Environment:** New/separate from tax-demo  
**Timeline:** 5 weeks  
**Goal:** Working Operations Squad with 3 agents

---

## Prerequisites (Day 0)

### **Install Required Software**

```bash
# 1. Check Node.js (need 20+)
node --version

# 2. Check Python (need 3.11+)
python3 --version

# 3. Check Docker
docker --version

# 4. Check AWS CLI
aws --version

# 5. Install AWS CDK globally
npm install -g aws-cdk

# 6. Verify CDK
cdk --version
```

### **Set Up AWS Account**

```bash
# Configure AWS CLI
aws configure
# Enter: Access Key, Secret Key, Region (us-west-2), Format (json)

# Verify access
aws sts get-caller-identity

# Bootstrap CDK (first time only)
cdk bootstrap
```

### **Create Project Directory**

```bash
# Create new directory
mkdir vela-operations-squad
cd vela-operations-squad

# Initialize git
git init
git branch -M main
```

---

## Step 1: Set Up Project Structure (Day 1 - 2 hours)

### **Create Directory Structure**

```bash
# Create folders
mkdir -p patterns/strands-multi-agent
mkdir -p gateway/tools/lead_response
mkdir -p gateway/tools/scheduler
mkdir -p gateway/tools/invoice_collection
mkdir -p gateway/layers/common/python
mkdir -p infra-cdk/lib
mkdir -p infra-cdk/bin
mkdir -p frontend/src
mkdir -p scripts
mkdir -p docs

# Create placeholder files
touch patterns/strands-multi-agent/__init__.py
touch gateway/tools/__init__.py
touch gateway/layers/common/python/__init__.py
```

### **Create Root Files**

**Create `README.md`:**
```markdown
# Vela Operations Squad

AI Squad for home services businesses.

## What It Does
- Responds to leads in 60 seconds
- Books appointments automatically
- Sends invoices and tracks payments

## Quick Start
See docs/START_HERE.md
```

**Create `.gitignore`:**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv

# Node
node_modules/
.next/
build/
dist/

# AWS
cdk.out/
.aws-sam/

# IDE
.vscode/
.idea/
*.swp

# Environment
.env
.env.local

# OS
.DS_Store
```

**Create `pyproject.toml`:**
```toml
[project]
name = "vela-operations-squad"
version = "0.1.0"
description = "AI Squad for home services operations"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## Step 2: Set Up Infrastructure (Day 1-2 - 6 hours)

### **Create CDK Project**

```bash
cd infra-cdk

# Initialize CDK project
npm init -y

# Install CDK dependencies
npm install aws-cdk-lib constructs
npm install @types/node typescript ts-node

# Create tsconfig.json
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["es2020"],
    "declaration": true,
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["bin/**/*", "lib/**/*"],
  "exclude": ["node_modules", "cdk.out"]
}
EOF

# Create cdk.json
cat > cdk.json << 'EOF'
{
  "app": "npx ts-node bin/vela-operations-squad.ts",
  "context": {
    "@aws-cdk/core:enableStackNameDuplicates": false,
    "@aws-cdk/core:stackRelativeExports": true
  }
}
EOF
```

### **Create Config File**

**Create `infra-cdk/config.yaml`:**
```yaml
# Vela Operations Squad Configuration

stack_name_base: vela-ops-squad

# Backend configuration
backend:
  pattern: strands-multi-agent
  deployment_type: docker

# SES Configuration
ses:
  from_email: noreply@yourdomain.com
  verified_domain: yourdomain.com

# Cost Optimization
cost_optimization:
  dynamodb_billing_mode: PROVISIONED
  lambda_architecture: ARM_64
  log_retention_days: 30
  s3_intelligent_tiering: true

# Memory Configuration
memory:
  retention_days: 120
  create_new: true  # Set to false after first deployment
```

---

## Step 3: Create DynamoDB Tables (Day 2 - 2 hours)

### **Create `infra-cdk/lib/database-stack.ts`:**

```typescript
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class DatabaseStack extends cdk.Stack {
  public readonly leadsTable: dynamodb.Table;
  public readonly appointmentsTable: dynamodb.Table;
  public readonly techniciansTable: dynamodb.Table;
  public readonly invoicesTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Leads Table
    this.leadsTable = new dynamodb.Table(this, 'LeadsTable', {
      tableName: `${id}-leads`,
      partitionKey: { name: 'lead_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // GSI for querying by org and status
    this.leadsTable.addGlobalSecondaryIndex({
      indexName: 'org_id-status-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });

    // Appointments Table
    this.appointmentsTable = new dynamodb.Table(this, 'AppointmentsTable', {
      tableName: `${id}-appointments`,
      partitionKey: { name: 'appointment_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.appointmentsTable.addGlobalSecondaryIndex({
      indexName: 'org_id-scheduled_time-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'scheduled_time', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });

    // Technicians Table
    this.techniciansTable = new dynamodb.Table(this, 'TechniciansTable', {
      tableName: `${id}-technicians`,
      partitionKey: { name: 'technician_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Invoices Table
    this.invoicesTable = new dynamodb.Table(this, 'InvoicesTable', {
      tableName: `${id}-invoices`,
      partitionKey: { name: 'invoice_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.invoicesTable.addGlobalSecondaryIndex({
      indexName: 'org_id-status-index',
      partitionKey: { name: 'org_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
    });
  }
}
```

**This creates 4 tables for the entire Operations Squad (all 3 agents share these tables).**

---

## Step 4: Build Lead Response Agent (Week 1 - Days 3-5)

### **Create Agent File**

**Create `patterns/strands-multi-agent/operations_squad.py`:**

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Vela Operations Squad

Multi-agent squad for home services operations.
Three agents: Lead Response, Scheduler, Invoice Collection
"""

import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands import Agent, Swarm
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

app = BedrockAgentCoreApp()

def create_operations_squad(user_id: str, session_id: str) -> Swarm:
    """
    Create Operations Squad with 3 agents.
    
    Args:
        user_id: Organization ID
        session_id: Session identifier
    
    Returns:
        Swarm with Lead Response, Scheduler, and Invoice agents
    """
    # Configure shared memory (4-layer system)
    memory_config = AgentCoreMemoryConfig(
        memory_id=os.environ['MEMORY_ID'],
        session_id=session_id,
        actor_id=user_id,
    )
    
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
    )
    
    # Get Gateway client for tools
    gateway_client = create_gateway_client()
    
    # Create Lead Response Agent
    lead_agent = Agent(
        name="LeadResponseAgent",
        system_prompt=get_lead_response_prompt(user_id),
        tools=[gateway_client],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.1
        ),
        session_manager=session_manager,
    )
    
    # Create Scheduler Agent
    scheduler_agent = Agent(
        name="SchedulerAgent",
        system_prompt=get_scheduler_prompt(),
        tools=[gateway_client],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.0
        ),
        session_manager=session_manager,
    )
    
    # Create Invoice Agent
    invoice_agent = Agent(
        name="InvoiceAgent",
        system_prompt=get_invoice_prompt(),
        tools=[gateway_client],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.0
        ),
        session_manager=session_manager,
    )
    
    # Create Swarm (multi-agent orchestration)
    squad = Swarm(
        agents=[lead_agent, scheduler_agent, invoice_agent],
        initial_agent=lead_agent,  # Always start with Lead Response
        max_handoffs=10,  # Prevent infinite loops
    )
    
    return squad

def create_gateway_client() -> MCPClient:
    """Create Gateway MCP client with OAuth2 authentication."""
    # Implementation here (similar to tax-demo)
    pass

def get_lead_response_prompt(user_id: str) -> str:
    """Get system prompt for Lead Response Agent."""
    return f"""You are a Lead Response Agent for a home services business.

Your role is to respond to customer inquiries instantly and qualify leads.

CRITICAL: You are assisting organization: {user_id}

When a lead comes in:
1. Greet them professionally
2. Ask qualifying questions (service needed, urgency, budget, location)
3. Determine if we can help
4. If qualified (score ≥ 7), hand off to SchedulerAgent
5. If not qualified, politely decline

Use handoff_to_agent tool when ready to hand off.

Be friendly, professional, and efficient. Respond within 60 seconds."""

def get_scheduler_prompt() -> str:
    """Get system prompt for Scheduler Agent."""
    return """You are an Appointment Scheduler Agent.

Your role is to book appointments for qualified leads.

When you receive a qualified lead:
1. Check technician availability
2. Find best time slot (consider skills, location, urgency)
3. Book the appointment
4. Send confirmation via email and SMS
5. Schedule reminders (24hr and 1hr before)
6. Hand off to InvoiceAgent to prepare invoice

Use handoff_to_agent tool when ready to hand off."""

def get_invoice_prompt() -> str:
    """Get system prompt for Invoice Agent."""
    return """You are an Invoice Collection Agent.

Your role is to handle billing and payment collection.

After appointment completion:
1. Generate invoice with service details
2. Send invoice via email with payment link
3. Track payment status
4. Send reminders if overdue (3, 7, 14, 30 days)
5. Offer payment plans if needed

Be professional and persistent but not aggressive."""

@app.entrypoint
async def operations_squad_handler(payload):
    """
    Main entrypoint for Operations Squad.
    
    Args:
        payload: Request with prompt, userId, runtimeSessionId
    
    Yields:
        Streaming response from squad
    """
    user_query = payload.get("prompt")
    user_id = payload.get("userId")
    session_id = payload.get("runtimeSessionId")
    
    # Create squad
    squad = create_operations_squad(user_id, session_id)
    
    # Stream response
    async for event in squad.stream_async(user_query):
        yield event

if __name__ == "__main__":
    app.run()
```

**Save this as:** `patterns/strands-multi-agent/operations_squad.py`

---

## Step 5: Build Lead Response Tool (Week 1 - Days 3-5)

### **Create Lambda Handler**

**Create `gateway/tools/lead_response/lead_response_lambda.py`:**

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Lead Response Tool

Monitors inquiries, qualifies leads, sends responses.
"""

import boto3
import json
import os
from datetime import datetime
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle lead response tool calls.
    
    Args:
        event: Tool call from Gateway
        context: Lambda context
    
    Returns:
        Tool response
    """
    # Extract tool name and parameters
    tool_name = event.get('tool_name')
    parameters = event.get('parameters', {})
    org_id = event.get('org_id')  # From Gateway auth
    
    # Route to appropriate handler
    if tool_name == 'qualify_lead':
        return qualify_lead(parameters, org_id)
    elif tool_name == 'send_response':
        return send_response(parameters, org_id)
    else:
        return {'error': f'Unknown tool: {tool_name}'}

def qualify_lead(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """
    Qualify and score a lead.
    
    Args:
        params: Lead details
        org_id: Organization ID
    
    Returns:
        Qualification result
    """
    # Extract lead details
    name = params.get('name')
    email = params.get('email')
    phone = params.get('phone')
    service_needed = params.get('service_needed')
    urgency = params.get('urgency', 'flexible')
    budget = params.get('budget')
    location = params.get('location')
    
    # Qualification logic
    score = 0
    
    # Has contact info? +3 points
    if email or phone:
        score += 3
    
    # Has service need? +2 points
    if service_needed:
        score += 2
    
    # Urgency? +2 points for emergency
    if urgency == 'emergency':
        score += 2
    elif urgency == 'this_week':
        score += 1
    
    # Has budget? +2 points
    if budget:
        score += 2
    
    # Has location? +1 point
    if location:
        score += 1
    
    # Determine if qualified (score ≥ 7)
    qualified = score >= 7
    
    # Store in DynamoDB
    leads_table = dynamodb.Table(os.environ['LEADS_TABLE'])
    lead_id = f"lead_{int(datetime.utcnow().timestamp() * 1000)}"
    
    leads_table.put_item(Item={
        'lead_id': lead_id,
        'org_id': org_id,
        'name': name or 'Unknown',
        'email': email or '',
        'phone': phone or '',
        'service_needed': service_needed or '',
        'urgency': urgency,
        'budget': budget or '',
        'location': location or '',
        'status': 'qualified' if qualified else 'not_qualified',
        'qualification_score': score,
        'created_at': datetime.utcnow().isoformat()
    })
    
    return {
        'lead_id': lead_id,
        'qualified': qualified,
        'score': score,
        'reason': f'Score: {score}/10. {"Qualified" if qualified else "Not qualified"}'
    }

def send_response(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """
    Send response to lead via email.
    
    Args:
        params: Response details
        org_id: Organization ID
    
    Returns:
        Send status
    """
    lead_id = params.get('lead_id')
    message = params.get('message')
    
    # Get lead details from database
    leads_table = dynamodb.Table(os.environ['LEADS_TABLE'])
    response = leads_table.get_item(
        Key={'lead_id': lead_id, 'org_id': org_id}
    )
    
    if 'Item' not in response:
        return {'error': 'Lead not found'}
    
    lead = response['Item']
    customer_email = lead.get('email')
    
    if not customer_email:
        return {'error': 'No email address for lead'}
    
    # Send email via SES
    try:
        ses.send_email(
            Source=os.environ['FROM_EMAIL'],
            Destination={'ToAddresses': [customer_email]},
            Message={
                'Subject': {'Data': 'Re: Your Service Request'},
                'Body': {'Text': {'Data': message}}
            }
        )
        
        return {
            'sent': True,
            'to': customer_email,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {'error': str(e)}
```

**Save this as:** `gateway/tools/lead_response/lead_response_lambda.py`

---

## Step 6: Deploy Infrastructure (Day 3 - 2 hours)

### **Create Main CDK Stack**

**Create `infra-cdk/bin/vela-operations-squad.ts`:**

```typescript
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { DatabaseStack } from '../lib/database-stack';

const app = new cdk.App();

new DatabaseStack(app, 'VelaOpsSquadDatabase', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  },
});
```

### **Deploy to AWS**

```bash
cd infra-cdk

# Synthesize CloudFormation templates
cdk synth

# Deploy (first time)
cdk deploy --all --require-approval never

# Save outputs
aws cloudformation describe-stacks \
  --stack-name VelaOpsSquadDatabase \
  --query 'Stacks[0].Outputs' > outputs.json
```

---

## Step 7: Test Lead Response Tool (Day 4 - 4 hours)

### **Create Test Script**

**Create `scripts/test_lead_response.py`:**

```python
#!/usr/bin/env python3

"""Test Lead Response Tool"""

import boto3
import json

# Initialize clients
lambda_client = boto3.client('lambda')

def test_qualify_lead():
    """Test lead qualification."""
    
    # Test case 1: Qualified lead
    payload = {
        'tool_name': 'qualify_lead',
        'parameters': {
            'name': 'John Smith',
            'email': 'john@example.com',
            'phone': '555-1234',
            'service_needed': 'HVAC repair',
            'urgency': 'emergency',
            'budget': '$2000',
            'location': '123 Main St'
        },
        'org_id': 'test_org_001'
    }
    
    response = lambda_client.invoke(
        FunctionName='lead-response-handler',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Test 1 - Qualified Lead: {result}")
    assert result['qualified'] == True
    assert result['score'] >= 7
    
    # Test case 2: Not qualified lead
    payload['parameters'] = {
        'name': 'Spam Bot',
        'service_needed': 'free quote'
    }
    
    response = lambda_client.invoke(
        FunctionName='lead-response-handler',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Test 2 - Not Qualified: {result}")
    assert result['qualified'] == False
    
    print("✅ All tests passed!")

if __name__ == '__main__':
    test_qualify_lead()
```

### **Run Tests**

```bash
python3 scripts/test_lead_response.py
```

---

## Step 8: Build Scheduler Agent (Week 2 - Days 6-10)

**Follow same pattern:**
1. Create `gateway/tools/scheduler/scheduler_lambda.py`
2. Implement: check_availability, book_appointment, send_confirmation
3. Deploy Lambda function
4. Test with `scripts/test_scheduler.py`
5. Verify handoff from Lead Response Agent works

---

## Step 9: Build Invoice Agent (Week 3 - Days 11-15)

**Follow same pattern:**
1. Create `gateway/tools/invoice_collection/invoice_collection_lambda.py`
2. Implement: generate_invoice, create_payment_link, send_invoice
3. Deploy Lambda function
4. Test with `scripts/test_invoice.py`
5. Verify handoff from Scheduler Agent works

---

## Step 10: Connect All Agents with Swarm (Week 4 - Days 16-20)

### **Test Complete Flow**

**Create `scripts/test_operations_squad.py`:**

```python
#!/usr/bin/env python3

"""Test complete Operations Squad flow"""

import asyncio
from operations_squad import create_operations_squad

async def test_complete_flow():
    """Test lead → schedule → invoice flow."""
    
    # Create squad
    squad = create_operations_squad(
        user_id='test_org_001',
        session_id='test_session_001'
    )
    
    # Simulate lead inquiry
    user_query = """
    New lead inquiry:
    Name: John Smith
    Email: john@example.com
    Phone: 555-1234
    Message: My AC stopped working, need help today
    """
    
    print("Testing Operations Squad...")
    print(f"Input: {user_query}")
    print("\nAgent responses:")
    
    # Stream response
    async for event in squad.stream_async(user_query):
        print(event)
    
    print("\n✅ Test complete!")

if __name__ == '__main__':
    asyncio.run(test_complete_flow())
```

### **Run End-to-End Test**

```bash
python3 scripts/test_operations_squad.py
```

**Expected output:**
```
Testing Operations Squad...
Input: New lead inquiry...

Agent responses:
LeadResponseAgent: Qualifying lead...
LeadResponseAgent: Lead qualified (score: 9/10)
LeadResponseAgent: Handing off to SchedulerAgent...
SchedulerAgent: Checking availability...
SchedulerAgent: Appointment booked for today at 4pm
SchedulerAgent: Confirmation sent
SchedulerAgent: Handing off to InvoiceAgent...
InvoiceAgent: Invoice prepared (draft)

✅ Test complete!
```

---

## Step 11: Deploy to Production (Week 4 - Day 20)

### **Final Deployment**

```bash
# 1. Build Docker image for agents
cd patterns/strands-multi-agent
docker build -t vela-operations-squad .

# 2. Deploy all infrastructure
cd ../../infra-cdk
cdk deploy --all --require-approval never

# 3. Verify deployment
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `Vela`)].StackName'

# 4. Test in production
cd ../scripts
python3 test_operations_squad.py --env production
```

---

## Step 12: Launch (Week 4 - Day 20)

### **Go Live Checklist**

- [ ] All 3 agents deployed
- [ ] All tools working
- [ ] Handoffs successful
- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] Documentation complete
- [ ] Beta customers ready
- [ ] Landing page live
- [ ] Payment processing working

### **Launch!**

```bash
# Turn on email monitoring
aws lambda update-function-configuration \
  --function-name lead-response-handler \
  --environment Variables={MONITORING_ENABLED=true}

# Agents are now live! 🚀
```

---

## Quick Reference

**Week 1:** Infrastructure + Lead Response Agent  
**Week 2:** Scheduler Agent  
**Week 3:** Invoice Agent  
**Week 4:** Integration + Launch  
**Week 5:** Scale to 15-20 customers  

**Total:** 5 weeks from start to launch

---

**Follow this step-by-step and you'll have a working Operations Squad! 🌟**
