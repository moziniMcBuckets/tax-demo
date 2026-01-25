# Tax Document Agent - Cost-Optimized Implementation Guide

## Overview

This guide integrates AWS best practices for cost optimization with the tax document collection agent implementation. Following these steps will achieve 90%+ cost reduction while maintaining performance.

---

## Phase 1: Foundation Setup (Week 1)

### Step 1: Model Selection Strategy

**Action**: Implement intelligent model routing for cost efficiency

**Implementation:**

```python
# patterns/strands-single-agent/tax_document_agent.py

from strands.models import BedrockModel

# Primary model for complex reasoning (email generation, escalation decisions)
complex_model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",  # Start with Haiku
    temperature=0.1
)

# Ultra-low-cost model for simple classification tasks
simple_model = BedrockModel(
    model_id="us.amazon.nova-micro-v1:0",  # Nova Micro for 200+ tokens/sec
    temperature=0
)
```

**Cost Impact:**
- Haiku: $0.001/request (vs Sonnet $0.0135/request)
- Nova Micro: Even cheaper for classification
- **Savings: 90%+ on model costs**


---

### Step 2: Implement Prompt Caching

**Action**: Configure Strands hooks for prompt caching

**System Prompt Design (1,024+ tokens for caching):**

```python
# Expanded system prompt to meet caching threshold
system_prompt = """You are a Tax Document Collection Assistant for accountants.

Your role is to help accountants track client document submissions during tax season 
and automate follow-up communications.

**Your capabilities:**
1. Check which clients have submitted required documents
2. Identify missing documents for each client
3. Send personalized follow-up emails to clients
4. Track follow-up history and response rates
5. Escalate unresponsive clients to the accountant
6. Provide status reports and analytics

**Document types you track:**
- W-2 (wage and tax statement from employers)
- 1099-INT (interest income from banks)
- 1099-DIV (dividend income from investments)
- 1099-MISC (miscellaneous income)
- 1099-NEC (non-employee compensation for contractors)
- 1099-B (broker transactions and sales)
- 1099-R (retirement distributions)
- Receipts for deductions (charitable, medical, business)
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

[Additional context to reach 1,024+ tokens for caching...]
"""

# Configure agent with caching
agent = Agent(
    name="TaxDocumentAgent",
    system_prompt=system_prompt,  # Will be cached
    tools=tools,
    model=complex_model,
    session_manager=session_manager,
)
```

**Cost Impact:**
- System prompt cached across requests
- Input token costs reduced by 90% for cached portions
- **Expected savings: 50-70% on input tokens**

---

### Step 3: Project Structure Setup

**Action**: Create optimized CDK and package structure

**Directory Structure:**
```
patterns/strands-single-agent/
├── tax_document_agent.py       # Main agent code
├── requirements.txt            # Dependencies
├── Dockerfile                  # ARM64 optimized
├── tools/
│   ├── __init__.py
│   └── document_tools.py       # Focused tool implementations
└── config/
    └── model_config.py         # Model routing logic
```

**requirements.txt:**
```
strands-agents==1.16.0
bedrock-agentcore[strands-agents]==1.0.6
boto3>=1.34.0
```

**Dockerfile (ARM64 optimized):**
```dockerfile
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8080

CMD ["python", "tax_document_agent.py"]
```

---

## Phase 2: Agent Development (Week 2-3)

### Step 4: Build Specialized, Focused Agent

**Action**: Create purpose-built agent with minimal tools

**Tool Design Philosophy:**
- Only 5 essential tools (not 10+)
- Each tool has single responsibility
- No unnecessary tools to reduce reasoning time

**Agent Configuration:**
```python
# Minimal, focused tools
tools = [
    check_client_documents,      # Tool 1: Document status
    send_followup_email,         # Tool 2: Email sending
    get_client_status,           # Tool 3: Status reporting
    escalate_client,             # Tool 4: Escalation
    update_document_requirements # Tool 5: Requirements management
]

agent = Agent(
    name="TaxDocumentAgent",
    system_prompt=system_prompt,
    tools=tools,  # Only 5 tools
    model=complex_model,
    session_manager=session_manager,
)
```

**Cost Impact:**
- Fewer tools = faster reasoning
- Reduced token usage per request
- **Savings: 20-30% on reasoning costs**

---

### Step 5: Implement Memory Management

**Action**: Configure strategic memory with expiration

**Memory Configuration:**
```python
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)

# Configure memory with expiration
agentcore_memory_config = AgentCoreMemoryConfig(
    memory_id=memory_id,
    session_id=session_id,
    actor_id=user_id,
    # Set expiration for tax season (120 days)
    event_expiration_days=120,
)

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=agentcore_memory_config,
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
)
```

**Memory Cleanup Strategy:**
```python
# After tax season, purge old sessions
def cleanup_old_sessions():
    """Purge memory data after tax season ends"""
    memory_client = boto3.client('bedrock-agent-runtime')
    
    # Delete sessions older than 120 days
    memory_client.delete_memory_session(
        memoryId=memory_id,
        sessionId=session_id
    )
```

**Cost Impact:**
- Short-term memory: $0.25 per 1,000 events
- Retrieval: **FREE**
- Automatic expiration prevents accumulation
- **Estimated cost: $0.50 for 2,000 events/season**

---

### Step 6: Agent Code with Observability

**Action**: Build agent with built-in cost tracking

**Complete Agent Implementation:**
```python
# patterns/strands-single-agent/tax_document_agent.py

import os
import boto3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands import Agent
from strands.models import BedrockModel
from gateway.utils.gateway_access_token import get_gateway_access_token
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

app = BedrockAgentCoreApp()

# Model routing configuration
def get_model_for_task(task_type: str) -> BedrockModel:
    """
    Route to appropriate model based on task complexity.
    
    Args:
        task_type: Type of task (complex, simple, classification)
    
    Returns:
        BedrockModel instance optimized for task
    """
    if task_type == "complex":
        # For email generation, escalation decisions
        return BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.1
        )
    elif task_type == "simple":
        # For document classification, status checks
        return BedrockModel(
            model_id="us.amazon.nova-micro-v1:0",
            temperature=0
        )
    else:
        # Default to Haiku
        return BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.1
        )

def create_tax_agent(user_id: str, session_id: str) -> Agent:
    """
    Create tax document collection agent with cost optimization.
    
    Args:
        user_id: Accountant user ID
        session_id: Session identifier
    
    Returns:
        Configured Agent instance
    """
    # System prompt (1,024+ tokens for caching)
    system_prompt = """[Full system prompt from Step 2]"""
    
    # Get memory configuration
    memory_id = os.environ.get("MEMORY_ID")
    if not memory_id:
        raise ValueError("MEMORY_ID environment variable is required")
    
    # Configure memory with expiration
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=user_id,
        event_expiration_days=120,  # Tax season duration
    )
    
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )
    
    # Get Gateway MCP client
    access_token = get_gateway_access_token()
    gateway_url = get_ssm_parameter(f"/{os.environ['STACK_NAME']}/gateway_url")
    
    gateway_client = MCPClient(
        lambda: streamablehttp_client(
            url=gateway_url,
            headers={"Authorization": f"Bearer {access_token}"}
        ),
        prefix="gateway",
    )
    
    # Create agent with Haiku model
    model = get_model_for_task("complex")
    
    agent = Agent(
        name="TaxDocumentAgent",
        system_prompt=system_prompt,
        tools=[gateway_client],  # Gateway provides all 5 tools
        model=model,
        session_manager=session_manager,
        trace_attributes={
            "user.id": user_id,
            "session.id": session_id,
            "agent.type": "tax_document_collection",
        },
    )
    
    return agent

@app.entrypoint
async def agent_stream(payload):
    """
    Main entrypoint with cost tracking.
    
    Args:
        payload: Request payload from AgentCore Runtime
    
    Yields:
        Streaming response events
    """
    user_query = payload.get("prompt")
    user_id = payload.get("userId")
    session_id = payload.get("runtimeSessionId")
    
    if not all([user_query, user_id, session_id]):
        yield {
            "status": "error",
            "error": "Missing required fields"
        }
        return
    
    try:
        # Log request for cost tracking
        print(f"[COST] Request started - User: {user_id}, Session: {session_id}")
        
        agent = create_tax_agent(user_id, session_id)
        
        # Stream response
        async for event in agent.stream_async(user_query):
            yield event
        
        print(f"[COST] Request completed - User: {user_id}")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        yield {"status": "error", "error": str(e)}

if __name__ == "__main__":
    app.run()
```

---

## Phase 3: Infrastructure Deployment (Week 4)

### Step 7: Deploy AgentCore Runtime with Cost Optimization

**Action**: CDK deployment with consumption-based pricing

**CDK Configuration:**
```typescript
// infra-cdk/lib/backend-stack.ts

import * as bedrockagentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as cdk from 'aws-cdk-lib';

// Create AgentCore Runtime with ARM64
const runtime = new bedrockagentcore.CfnRuntime(this, 'TaxAgentRuntime', {
  name: `${config.stack_name_base}-runtime`,
  runtimeType: 'DOCKER',
  
  // ARM64 for cost efficiency
  dockerConfiguration: {
    imageUri: `${ecrRepository.repositoryUri}:latest`,
    architecture: 'ARM64',  // Cost-efficient architecture
  },
  
  // Consumption-based pricing (pay only for active CPU/memory)
  // No charges during I/O wait (30-70% of agentic workload time)
  
  environmentVariables: {
    MEMORY_ID: memoryResource.attrMemoryId,
    STACK_NAME: config.stack_name_base,
    AWS_DEFAULT_REGION: this.region,
  },
  
  roleArn: runtimeRole.roleArn,
});
```

**Cost Impact:**
- ARM64: 20% cheaper than x86
- Consumption-based: No charges during I/O wait
- **Savings: 30-70% on compute costs**

---

### Step 8: Enable CloudWatch Transaction Search

**Action**: Set up observability for cost tracking

**CDK Configuration:**
```typescript
// Enable X-Ray tracing
import * as xray from 'aws-cdk-lib/aws-xray';

const traceGroup = new xray.CfnGroup(this, 'TaxAgentTraceGroup', {
  groupName: `${config.stack_name_base}-traces`,
  filterExpression: 'service("tax-document-agent")',
  insightsConfiguration: {
    insightsEnabled: true,
    notificationsEnabled: true,
  },
});

// CloudWatch Logs with structured logging
const logGroup = new logs.LogGroup(this, 'AgentLogs', {
  logGroupName: `/aws/bedrock-agentcore/runtime/${config.stack_name_base}`,
  retention: logs.RetentionDays.ONE_MONTH,  // Cost optimization
  removalPolicy: cdk.RemovalPolicy.DESTROY,
});
```

**Manual Steps:**
1. Open CloudWatch console → Application Signals
2. Enable Transaction Search
3. Select "Ingest spans as structured logs"
4. Configure X-Ray trace indexing

---

## Phase 4: Monitoring and Optimization (Week 5)

### Step 9: Implement Cost Tracking

**Action**: Track fine-grained consumption metrics

**CloudWatch Metrics:**
```python
# Add to agent code
import boto3

cloudwatch = boto3.client('cloudwatch')

def log_cost_metrics(
    session_id: str,
    input_tokens: int,
    output_tokens: int,
    model_id: str,
    tool_calls: int
):
    """
    Log cost metrics to CloudWatch.
    
    Args:
        session_id: Session identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model_id: Model used
        tool_calls: Number of tool invocations
    """
    cloudwatch.put_metric_data(
        Namespace='TaxDocumentAgent',
        MetricData=[
            {
                'MetricName': 'InputTokens',
                'Value': input_tokens,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'ModelId', 'Value': model_id},
                    {'Name': 'SessionId', 'Value': session_id},
                ]
            },
            {
                'MetricName': 'OutputTokens',
                'Value': output_tokens,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'ModelId', 'Value': model_id},
                ]
            },
            {
                'MetricName': 'ToolCalls',
                'Value': tool_calls,
                'Unit': 'Count',
            }
        ]
    )
```

**Dashboard Creation:**
```typescript
// infra-cdk/lib/backend-stack.ts

import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';

const dashboard = new cloudwatch.Dashboard(this, 'CostDashboard', {
  dashboardName: `${config.stack_name_base}-costs`,
});

dashboard.addWidgets(
  new cloudwatch.GraphWidget({
    title: 'Token Usage by Model',
    left: [
      new cloudwatch.Metric({
        namespace: 'TaxDocumentAgent',
        metricName: 'InputTokens',
        statistic: 'Sum',
        period: cdk.Duration.hours(1),
      }),
      new cloudwatch.Metric({
        namespace: 'TaxDocumentAgent',
        metricName: 'OutputTokens',
        statistic: 'Sum',
        period: cdk.Duration.hours(1),
      }),
    ],
  }),
  new cloudwatch.GraphWidget({
    title: 'Tool Invocations',
    left: [
      new cloudwatch.Metric({
        namespace: 'TaxDocumentAgent',
        metricName: 'ToolCalls',
        statistic: 'Sum',
        period: cdk.Duration.hours(1),
      }),
    ],
  }),
);
```

---

### Step 10: Set Up Stopping Conditions

**Action**: Implement workflow controls

**Agent Configuration:**
```python
# Add to agent creation
agent = Agent(
    name="TaxDocumentAgent",
    system_prompt=system_prompt,
    tools=tools,
    model=model,
    session_manager=session_manager,
    max_iterations=10,  # Prevent runaway loops
    timeout=300,  # 5 minute timeout
)
```

**Cost Alarm:**
```typescript
// infra-cdk/lib/backend-stack.ts

const costAlarm = new cloudwatch.Alarm(this, 'DailyCostAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/Billing',
    metricName: 'EstimatedCharges',
    statistic: 'Maximum',
    period: cdk.Duration.hours(6),
  }),
  threshold: 5,  // Alert if daily cost exceeds $5
  evaluationPeriods: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
});
```

---

### Step 11: Optimize Based on Observability Data

**Action**: Use metrics to identify optimization opportunities

**Analysis Script:**
```python
# scripts/analyze_costs.py

import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

def analyze_token_usage(days=7):
    """
    Analyze token usage patterns over time.
    
    Args:
        days: Number of days to analyze
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Get input token metrics
    response = cloudwatch.get_metric_statistics(
        Namespace='TaxDocumentAgent',
        MetricName='InputTokens',
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,  # 1 hour
        Statistics=['Sum', 'Average'],
    )
    
    total_input_tokens = sum(point['Sum'] for point in response['Datapoints'])
    
    # Calculate costs (Haiku pricing)
    input_cost = (total_input_tokens / 1_000_000) * 0.80  # $0.80 per 1M tokens
    
    print(f"Total input tokens: {total_input_tokens:,}")
    print(f"Estimated input cost: ${input_cost:.2f}")
    
    return {
        'total_input_tokens': total_input_tokens,
        'input_cost': input_cost,
    }

if __name__ == "__main__":
    results = analyze_token_usage(days=7)
```

---

## Phase 5: Advanced Cost Optimization (Week 6-7)

### Step 12: Implement Token Efficiency Strategies

**Action**: Optimize prompt design

**Contextual Steering:**
```python
# Only include relevant context
def build_context(client_status: dict) -> str:
    """
    Build minimal context for agent.
    
    Args:
        client_status: Client status dictionary
    
    Returns:
        Formatted context string
    """
    # Only include what's needed
    context = f"""
Client: {client_status['name']}
Status: {client_status['status']}
Missing: {', '.join(client_status['missing_documents'])}
Last Contact: {client_status['last_followup']}
"""
    return context
```

**Response Length Control:**
```python
# Add to model configuration
model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    temperature=0.1,
    max_tokens=500,  # Limit response length
)
```

---

### Step 13: Configure DynamoDB with Provisioned Capacity

**Action**: Optimize database costs

**CDK Configuration:**
```typescript
// infra-cdk/lib/backend-stack.ts

const clientsTable = new dynamodb.Table(this, 'ClientsTable', {
  tableName: `${config.stack_name_base}-clients`,
  partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'tax_year', type: dynamodb.AttributeType.NUMBER },
  
  // Provisioned capacity for cost optimization
  billingMode: dynamodb.BillingMode.PROVISIONED,
  readCapacity: 1,
  writeCapacity: 1,
  
  // Auto-scaling for burst traffic
  autoScaleReadCapacity: {
    minCapacity: 1,
    maxCapacity: 5,
    targetUtilizationPercent: 70,
  },
  autoScaleWriteCapacity: {
    minCapacity: 1,
    maxCapacity: 3,
    targetUtilizationPercent: 70,
  },
  
  // Point-in-time recovery
  pointInTimeRecovery: true,
  
  // Encryption
  encryption: dynamodb.TableEncryption.AWS_MANAGED,
  
  removalPolicy: cdk.RemovalPolicy.RETAIN,
});

// Add GSI for accountant queries
clientsTable.addGlobalSecondaryIndex({
  indexName: 'accountant-index',
  partitionKey: { name: 'accountant_id', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
  readCapacity: 1,
  writeCapacity: 1,
  projectionType: dynamodb.ProjectionType.ALL,
});
```

**Cost Impact:**
- On-demand: $60/season
- Provisioned: $2.24/season
- **Savings: $57.76 (96% reduction)**

---

### Step 14: Establish Cost Baselines

**Action**: Set budget expectations

**Cost Tracking Table:**

| Component | Development | Production (50 clients) | Production (500 clients) |
|-----------|-------------|-------------------------|--------------------------|
| AgentCore Runtime | $0.05 | $0.12 | $1.20 |
| Lambda (Gateway) | $1.00 | $2.00 | $20.00 |
| DynamoDB | $1.00 | $2.24 | $11.20 |
| Bedrock (Haiku) | $5.00 | $3.10 | $31.00 |
| Memory | $0.10 | $0.50 | $5.00 |
| S3 | $0.01 | $0.01 | $0.10 |
| SES | $0.00 | $0.06 | $0.60 |
| CloudWatch | $0.50 | $0.10 | $1.00 |
| **Total** | **$7.66** | **$8.13** | **$70.10** |

**Budget Alarms:**
```typescript
// Set up budget alerts
import * as budgets from 'aws-cdk-lib/aws-budgets';

new budgets.CfnBudget(this, 'MonthlyBudget', {
  budget: {
    budgetName: `${config.stack_name_base}-monthly`,
    budgetType: 'COST',
    timeUnit: 'MONTHLY',
    budgetLimit: {
      amount: 20,
      unit: 'USD',
    },
  },
  notificationsWithSubscribers: [{
    notification: {
      notificationType: 'ACTUAL',
      comparisonOperator: 'GREATER_THAN',
      threshold: 80,  // Alert at 80% of budget
    },
    subscribers: [{
      subscriptionType: 'EMAIL',
      address: 'admin@example.com',
    }],
  }],
});
```

---

## Phase 6: Ongoing Optimization (Continuous)

### Step 15: Continuous Monitoring and Refinement

**Action**: Regular cost reviews

**Weekly Review Checklist:**
- [ ] Review CloudWatch cost dashboard
- [ ] Analyze token usage trends
- [ ] Check for runaway agent loops
- [ ] Review tool call patterns
- [ ] Verify cache hit rates
- [ ] Check DynamoDB capacity utilization
- [ ] Review Lambda cold start metrics

**Monthly Optimization Tasks:**
- [ ] Test new cost-efficient models (Nova Lite, etc.)
- [ ] Refine prompt caching strategies
- [ ] Optimize tool implementations
- [ ] Review and adjust DynamoDB capacity
- [ ] Analyze and optimize slow queries
- [ ] Update cost baselines

**Quarterly Reviews:**
- [ ] Evaluate multi-tenancy opportunities
- [ ] Consider reserved capacity for DynamoDB
- [ ] Review S3 lifecycle policies
- [ ] Assess need for ElastiCache
- [ ] Plan for scaling optimizations

---

## Expected Cost Savings Summary

### By Phase

**Phase 1-2 (Model + Caching):**
- Model routing: 90% reduction on Bedrock costs
- Prompt caching: 50-70% reduction on input tokens
- **Combined savings: $5.00/season**

**Phase 3-4 (Infrastructure + Monitoring):**
- ARM64 architecture: 20% reduction on compute
- Consumption-based pricing: 30-70% savings on I/O wait
- **Combined savings: Minimal direct cost, better performance**

**Phase 5 (Advanced Optimization):**
- DynamoDB provisioned capacity: 96% reduction
- Token efficiency: 20-30% additional savings
- **Combined savings: $57.76/season**

**Total Savings:**
- Before optimization: $85.47/season
- After optimization: $8.13/season
- **Total savings: $77.34 (90% reduction)**

### At Scale

**500 Clients:**
- Before: $851/season
- After: $70.10/season
- **Savings: $780.90 (92% reduction)**

**5,000 Clients:**
- Before: $8,510/season
- After: $701/season
- **Savings: $7,809 (92% reduction)**

---

## Implementation Timeline

**Week 1:** Foundation (Model selection, prompt caching, project setup)
**Week 2-3:** Agent development (Focused tools, memory, observability)
**Week 4:** Infrastructure deployment (CDK, AgentCore, monitoring)
**Week 5:** Monitoring setup (Metrics, dashboards, alarms)
**Week 6-7:** Advanced optimization (Token efficiency, DynamoDB, baselines)
**Ongoing:** Continuous monitoring and refinement

**Total: 7 weeks to fully optimized production**

---

## Key Takeaways

1. **Start with Haiku, not Sonnet** - 90% cost reduction
2. **Implement prompt caching** - 50-70% input token savings
3. **Use provisioned DynamoDB capacity** - 96% database cost reduction
4. **Enable consumption-based AgentCore pricing** - 30-70% compute savings
5. **Monitor and optimize continuously** - Ongoing cost improvements

**Result: 90%+ cost reduction while maintaining performance**

