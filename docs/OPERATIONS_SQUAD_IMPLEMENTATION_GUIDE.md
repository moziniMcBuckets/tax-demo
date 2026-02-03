# Operations Squad: Implementation Guide with Swarm Pattern

**Framework:** Strands SDK 1.0+ with Swarm pattern  
**Model Strategy:** Optimized for cost and performance  
**Timeline:** 5 weeks

---

## Model Selection Strategy

### **Recommended Models for Operations Squad**

**Primary Model: Claude 3.5 Haiku (Cost-Optimized)**
- **Use for:** All three agents (Lead Response, Scheduler, Invoice)
- **Why:** 90% cheaper than Sonnet, sufficient for operational tasks
- **Cost:** $0.0008/1K input tokens, $0.0016/1K output tokens
- **Parameters:**
  - Temperature: 0.1 (analytical precision)
  - Max tokens: 2048 (sufficient for responses)
- **Best for:** Structured workflows, tool calling, consistent responses

**Alternative: Meta Llama 4 (If Available)**
- **Use for:** Complex multi-agent coordination
- **Why:** Extensive context windows, multimodal capabilities
- **When:** If you need longer context or more complex reasoning
- **Cost:** Check Bedrock pricing (likely similar to Haiku)

**Fallback: Claude 3.5 Sonnet**
- **Use for:** Complex edge cases only
- **Why:** Better reasoning for ambiguous situations
- **Cost:** 10x more expensive than Haiku
- **When:** Only if Haiku fails (< 5% of cases)

### **Model Configuration**

**For Lead Response Agent:**
```
Model: Claude 3.5 Haiku
Temperature: 0.1 (consistent, professional responses)
Max tokens: 1024 (short responses)
Top P: 0.9
```

**For Scheduler Agent:**
```
Model: Claude 3.5 Haiku
Temperature: 0.0 (deterministic booking)
Max tokens: 512 (confirmations only)
Top P: 1.0
```

**For Invoice Agent:**
```
Model: Claude 3.5 Haiku
Temperature: 0.0 (accurate calculations)
Max tokens: 1024 (invoice details)
Top P: 1.0
```

---

## Swarm Pattern Implementation

### **What is Swarm?**

Swarm is a multi-agent pattern where:
- Agents autonomously decide who should handle next step
- Agents use `handoff_to_agent` tool to pass control
- All agents share context via shared memory
- Execution is sequential but routing is dynamic

### **How Swarm Works for Operations Squad**

**Flow:**
```
User: "New lead inquiry"
    ↓
Lead Response Agent:
  - Processes inquiry
  - Qualifies lead
  - Decides: "This is qualified, Scheduler should handle"
  - Calls: handoff_to_agent(target="SchedulerAgent", context={...})
    ↓
Scheduler Agent:
  - Receives handoff with full context
  - Checks availability
  - Books appointment
  - Decides: "Booking complete, Invoice should prepare"
  - Calls: handoff_to_agent(target="InvoiceAgent", context={...})
    ↓
Invoice Agent:
  - Receives handoff with full context
  - Prepares draft invoice
  - Waits for appointment completion
  - Sends invoice when triggered
```

### **Swarm Configuration**

**Initialize Swarm:**
```
from strands import Swarm, Agent

# Create agents
lead_agent = Agent(
    name="LeadResponseAgent",
    system_prompt=lead_response_prompt,
    tools=[monitor_email, qualify_lead, send_response, handoff_to_agent],
    model=BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0", temperature=0.1)
)

scheduler_agent = Agent(
    name="SchedulerAgent",
    system_prompt=scheduler_prompt,
    tools=[check_availability, book_appointment, send_confirmation, handoff_to_agent],
    model=BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0", temperature=0.0)
)

invoice_agent = Agent(
    name="InvoiceAgent",
    system_prompt=invoice_prompt,
    tools=[generate_invoice, send_invoice, track_payment],
    model=BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0", temperature=0.0)
)

# Create swarm
operations_squad = Swarm(
    agents=[lead_agent, scheduler_agent, invoice_agent],
    initial_agent=lead_agent  # Always start with Lead Response
)
```

---

## Memory Management (Four-Layer System)

### **Layer 1: User Preference Memory Strategy**

**Purpose:** Maintain user-specific configurations and adapt agent behavior

**Implementation:**
- **Namespace:** `/users/{org_id}` (organization-level isolation)
- **Storage:** AgentCore Memory + DynamoDB settings table
- **Retention:** Permanent (until customer cancels)
- **Access:** All agents can read/write

**What it stores:**
- Business settings (hours, service area, pricing)
- Technician preferences (skills, availability patterns)
- Customer preferences (communication style, booking preferences)
- Historical patterns (peak times, common services)

**Example:**
```
User Preference Memory for org_123:
{
  "business_hours": "Mon-Fri 8am-6pm, Sat 9am-3pm",
  "service_area": "50 mile radius from 12345",
  "pricing": {
    "HVAC_repair": "$150/hour",
    "emergency_fee": "$75"
  },
  "preferences": {
    "response_tone": "professional_friendly",
    "booking_buffer": "30_minutes",
    "reminder_timing": "24h_and_1h"
  },
  "patterns": {
    "peak_hours": "Mon-Wed 9am-11am",
    "common_services": ["HVAC", "plumbing"],
    "average_job_value": "$2000"
  }
}
```

**How agents use it:**
- Lead Response Agent: Adapts tone based on preferences
- Scheduler Agent: Respects booking buffer and peak hours
- Invoice Agent: Uses correct pricing and payment terms

---

### **Layer 2: Semantic Memory Strategy**

**Purpose:** Contextual understanding and knowledge retention across sessions

**Implementation:**
- **Storage:** AgentCore Memory (vector embeddings)
- **Namespace:** `/semantic/{org_id}`
- **Retention:** 120 days
- **Access:** All agents can search semantically

**What it stores:**
- Customer interaction history
- Service patterns and trends
- Problem-solution pairs
- Successful conversation flows

**Example:**
```
Semantic Memory:
- "Customer John Smith always books morning appointments"
- "Emergency HVAC calls usually need same-day service"
- "Customers asking about 'AC not cooling' typically need refrigerant"
- "Payment plans work well for jobs over $1,000"
```

**How agents use it:**
- Lead Response Agent: "I see you've worked with us before, John!"
- Scheduler Agent: "Based on your history, would morning work?"
- Invoice Agent: "Would you like a payment plan? (job > $1K)"

**Implementation:**
```
# Query semantic memory
relevant_context = memory.search(
    query="customer preferences for John Smith",
    namespace=f"/semantic/{org_id}",
    top_k=5
)

# Agent uses context to personalize response
agent_prompt = f"""
Based on previous interactions:
{relevant_context}

Respond to this customer appropriately.
"""
```

---

### **Layer 3: Session Summary Strategy**

**Purpose:** Maintain session-level summaries and conversation context

**Implementation:**
- **Storage:** AgentCore Memory (session context)
- **Namespace:** `/sessions/{session_id}`
- **Retention:** 120 days
- **Access:** All agents in current session

**What it stores:**
- Current conversation summary
- Key decisions made
- Information collected
- Next steps planned

**Example:**
```
Session Summary for session_abc123:
{
  "summary": "Customer John Smith needs emergency HVAC repair. 
              Qualified (score 9/10). Appointment booked for today 
              at 4pm with technician Mike. Invoice prepared.",
  "key_info": {
    "customer": "John Smith, 555-1234, john@example.com",
    "service": "Emergency HVAC repair",
    "urgency": "Same day",
    "budget": "$2000",
    "address": "123 Main St"
  },
  "decisions": [
    "Qualified as high-priority lead",
    "Assigned to Mike (HVAC specialist)",
    "Booked same-day appointment"
  ],
  "next_steps": [
    "Mike arrives at 4pm",
    "Complete service",
    "Send invoice"
  ]
}
```

**How agents use it:**
- Each agent sees full session context
- No need to re-ask questions
- Smooth handoffs with context
- Coherent conversation across agents

**Implementation:**
```
# Strands automatically manages session summaries
# Just configure session manager

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=org_id
    ),
    region_name=aws_region
)

# All agents share this session manager
# Summaries are automatic
```

---

### **Layer 4: Custom Memory Strategy (Issue Tracking)**

**Purpose:** Track specific issues, edge cases, and incident patterns

**Implementation:**
- **Storage:** DynamoDB custom_issues table + AgentCore Memory
- **Namespace:** `/issues/{org_id}`
- **Retention:** 365 days
- **Access:** All agents can log and query

**What it stores:**
- Edge cases encountered
- Error patterns
- Customer complaints
- Resolution strategies
- Learning opportunities

**Example:**
```
Custom Issue Log:
{
  "issue_id": "issue_001",
  "type": "scheduling_conflict",
  "description": "Double-booked technician due to calendar sync delay",
  "resolution": "Implemented 5-minute buffer between appointments",
  "learned": "Always check calendar twice before confirming",
  "occurred_at": "2026-02-01T14:30:00Z",
  "resolved_at": "2026-02-01T14:45:00Z",
  "impact": "Customer rescheduled, no revenue loss"
}
```

**How agents use it:**
- Query before making decisions: "Has this situation happened before?"
- Learn from past issues: "Last time we did X, it worked"
- Avoid repeating mistakes: "Don't do Y, it caused problems"
- Improve over time: "We've handled 50 similar cases successfully"

**Implementation:**
```
# Custom extraction prompt for issue tracking
issue_extraction_prompt = """
Analyze this interaction and extract any issues or edge cases:
- What went wrong?
- How was it resolved?
- What should we learn?
- How can we prevent this?

Format as structured JSON.
"""

# Custom consolidation prompt
issue_consolidation_prompt = """
Consolidate these similar issues into patterns:
- Common root causes
- Effective solutions
- Prevention strategies

Provide actionable insights.
"""

# Use in agents
if error_detected:
    memory.store_custom(
        namespace=f"/issues/{org_id}",
        content=issue_details,
        extraction_prompt=issue_extraction_prompt
    )
```

---

### **Memory Configuration for Production**

**First Deployment:**
```yaml
# config.yaml
memory:
  create_new: true
  retention_days: 120
  namespaces:
    - /users/{org_id}
    - /semantic/{org_id}
    - /sessions/{session_id}
    - /issues/{org_id}
```

**After First Deployment:**
```yaml
# config.yaml (updated)
memory:
  use_existing: true
  memory_id: "mem_abc123xyz"  # From deployment logs
  retention_days: 120
```

**Why reuse memory:**
- Preserves all learned patterns
- Maintains customer preferences
- Keeps historical context
- Avoids re-learning

---

### **Memory Access Patterns**

**Read Pattern (Agent needs context):**
```
1. Agent receives request
2. Agent queries relevant memory layers:
   - User preferences: "What are business hours?"
   - Semantic memory: "What do I know about this customer?"
   - Session summary: "What happened so far?"
   - Issue tracking: "Have we seen this before?"
3. Agent uses context to make decision
4. Agent responds appropriately
```

**Write Pattern (Agent learns something):**
```
1. Agent completes action
2. Agent stores in appropriate layer:
   - User preference: "Customer prefers morning appointments"
   - Semantic memory: "Emergency calls need same-day service"
   - Session summary: "Appointment booked for 4pm"
   - Issue tracking: "Calendar sync failed, used fallback"
3. Memory persisted for future use
```

**Update Pattern (Agent refines knowledge):**
```
1. Agent encounters new information
2. Agent queries existing memory
3. Agent updates or appends:
   - Preference changed: Update user preference
   - Pattern refined: Update semantic memory
   - Issue resolved: Update issue tracking
4. Memory stays current and accurate
```

### **Memory Configuration**

**AgentCore Memory Setup:**
```
memory_config = AgentCoreMemoryConfig(
    memory_id=os.environ['MEMORY_ID'],
    session_id=session_id,
    actor_id=org_id,  # Isolate by organization
    retention_days=120  # 4 months
)

session_manager = AgentCoreMemorySessionManager(
    agentcore_memory_config=memory_config,
    region_name=os.environ['AWS_DEFAULT_REGION']
)

# All agents share this session manager
lead_agent = Agent(..., session_manager=session_manager)
scheduler_agent = Agent(..., session_manager=session_manager)
invoice_agent = Agent(..., session_manager=session_manager)
```

---

## Advanced Orchestration Techniques

### **Technique 1: ReWOO (Reasoning Without Observation)**

**What it is:** Separate planning, execution, and synthesis

**How to use:**
```
Planning Phase (Lead Response Agent):
  - Analyze: What does customer need?
  - Plan: Steps to handle this lead
  - Output: Plan = [qualify, schedule, invoice]

Execution Phase (All Agents):
  - Execute: Each agent executes their step
  - No re-planning during execution
  - Faster and more predictable

Synthesis Phase (Final Agent):
  - Combine: Results from all agents
  - Output: Final response to customer
```

**When to use:** Complex workflows with multiple steps

**For Operations Squad:** Not needed initially (workflow is straightforward)

---

### **Technique 2: Reflexion (Iterative Refinement)**

**What it is:** Agent critiques its own output and improves

**How to use:**
```
Initial Response (Lead Response Agent):
  - Draft: "Hi, we can help with your plumbing issue"
  
Critique Phase:
  - Evaluate: Is this response professional? Personalized? Complete?
  - Identify: Missing customer name, no urgency acknowledgment
  
Refinement Phase:
  - Improve: "Hi John, thanks for reaching out about your emergency 
             plumbing issue. We can help right away!"
```

**When to use:** Customer-facing communications that need to be perfect

**For Operations Squad:** Use for Lead Response Agent (customer's first impression matters)

---

### **Technique 3: Typed Handoffs**

**What it is:** Enforce data contracts between agents

**How to use:**
```
from pydantic import BaseModel

class LeadContext(BaseModel):
    lead_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    service_needed: str
    urgency: str
    qualification_score: int

# Lead Response Agent hands off with typed context
handoff_to_agent(
    target="SchedulerAgent",
    context=LeadContext(
        lead_id="lead_123",
        customer_name="John Smith",
        ...
    )
)

# Scheduler Agent receives typed context
# Guaranteed to have all required fields
```

**When to use:** Always (prevents errors from missing data)

**For Operations Squad:** Implement for all handoffs

---

## Agent-to-Agent (A2A) Protocol

### **What is A2A?**

Open standard for cross-platform agent communication. Agents can be on different platforms and communicate via HTTP.

### **When to Use A2A**

**Use A2A for:**
- Cross-organization collaboration (customer's agent talks to your agent)
- External agent integration (integrate with third-party AI agents)
- Microservices architecture (agents deployed separately)

**Don't use A2A for:**
- MVP (all agents in same deployment)
- Simple handoffs (Swarm handles this)
- Same-platform agents (unnecessary overhead)

### **Future Use Case**

**Year 2: White-label deployments**
- Each customer gets their own agent deployment
- Agents communicate via A2A protocol
- Enables multi-tenant isolation at agent level

**For now:** Skip A2A. Use Swarm handoffs (simpler, faster).

---

## Implementation Checklist

### **Week 1: Lead Response Agent**

**Infrastructure:**
- [ ] Set up DynamoDB leads table
- [ ] Set up Lambda for email monitoring
- [ ] Set up Lambda for lead qualification
- [ ] Set up Lambda for response sending
- [ ] Configure Gmail API OAuth
- [ ] Configure Twilio for SMS

**Agent:**
- [ ] Write system prompt
- [ ] Configure model (Haiku, temp=0.1)
- [ ] Add tools (monitor, qualify, respond)
- [ ] Add handoff_to_agent tool
- [ ] Configure memory (AgentCore Memory)
- [ ] Test with sample leads

**Testing:**
- [ ] Send 10 test emails
- [ ] Verify responses < 60 seconds
- [ ] Verify qualification accuracy > 80%
- [ ] Verify handoffs work

---

### **Week 2: Scheduler Agent**

**Infrastructure:**
- [ ] Set up DynamoDB appointments table
- [ ] Set up DynamoDB technicians table
- [ ] Set up Lambda for availability checking
- [ ] Set up Lambda for booking
- [ ] Set up Lambda for confirmations
- [ ] Configure Google Calendar API
- [ ] Configure EventBridge for reminders

**Agent:**
- [ ] Write system prompt
- [ ] Configure model (Haiku, temp=0.0)
- [ ] Add tools (check, book, confirm)
- [ ] Add handoff_to_agent tool
- [ ] Share memory with Lead Response Agent
- [ ] Test with qualified leads

**Testing:**
- [ ] Test availability checking
- [ ] Test booking (no conflicts)
- [ ] Test confirmations sent
- [ ] Test reminders scheduled
- [ ] Test handoff from Lead Response

---

### **Week 3: Invoice Agent**

**Infrastructure:**
- [ ] Set up DynamoDB invoices table
- [ ] Set up Lambda for invoice generation
- [ ] Set up Lambda for payment tracking
- [ ] Set up Lambda for reminders
- [ ] Configure Stripe API
- [ ] Configure QuickBooks API (optional)

**Agent:**
- [ ] Write system prompt
- [ ] Configure model (Haiku, temp=0.0)
- [ ] Add tools (generate, send, track)
- [ ] Share memory with other agents
- [ ] Test with completed appointments

**Testing:**
- [ ] Test invoice generation
- [ ] Test payment links work
- [ ] Test payment tracking
- [ ] Test reminders sent
- [ ] Test handoff from Scheduler

---

### **Week 4: Swarm Integration**

**Connect All Agents:**
- [ ] Initialize Swarm with all 3 agents
- [ ] Configure shared memory
- [ ] Test handoffs: Lead → Scheduler
- [ ] Test handoffs: Scheduler → Invoice
- [ ] Test full flow: Lead → Schedule → Invoice

**Error Handling:**
- [ ] Handle: Agent fails to respond
- [ ] Handle: Tool call fails
- [ ] Handle: Handoff fails
- [ ] Handle: External API down
- [ ] Implement: Retry logic
- [ ] Implement: Fallback to human

**Monitoring:**
- [ ] Set up CloudWatch dashboards
- [ ] Set up X-Ray tracing
- [ ] Set up alerts (error rate, response time)
- [ ] Log all handoffs
- [ ] Track performance metrics

---

### **Week 5: Polish & Deploy**

**Optimization:**
- [ ] Optimize prompts (reduce tokens)
- [ ] Enable prompt caching (50-70% savings)
- [ ] Optimize database queries
- [ ] Implement caching (Redis)
- [ ] Reduce Lambda cold starts

**Production Deployment:**
- [ ] Deploy to production AWS account
- [ ] Configure custom domain
- [ ] Set up monitoring
- [ ] Enable auto-scaling
- [ ] Test with beta customers

**Documentation:**
- [ ] User guide
- [ ] API documentation
- [ ] Troubleshooting guide
- [ ] Video tutorials

---

## Cost Optimization

### **Prompt Caching**

**Enable for system prompts > 1,024 tokens:**
- Lead Response Agent prompt: ~1,500 tokens → Cache eligible
- Scheduler Agent prompt: ~1,200 tokens → Cache eligible
- Invoice Agent prompt: ~1,000 tokens → Cache eligible

**Savings:** 50-70% on input tokens

**Implementation:**
```
# Strands automatically handles prompt caching
# Just ensure system prompts are > 1,024 tokens
# Add detailed instructions to reach threshold
```

### **Model Switching**

**Use cheaper models when possible:**
- Simple classification: Use Nova Micro ($0.000035/1K tokens)
- Complex reasoning: Use Haiku ($0.0008/1K tokens)
- Critical decisions: Use Sonnet ($0.003/1K tokens)

**Implementation:**
```
# Create model factory
def get_model_for_task(task_type: str):
    if task_type == "simple":
        return BedrockModel(model_id="us.amazon.nova-micro-v1:0")
    elif task_type == "complex":
        return BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
    else:
        return BedrockModel(model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0")

# Use in agents
lead_agent = Agent(
    model=get_model_for_task("complex")  # Haiku for lead response
)
```

---

## Best Practices for Swarm Implementation

### **1. Model-Driven Behavior**

**Let the model decide:**
- Which agent should handle next
- When to hand off
- How to handle edge cases

**Don't hardcode:**
- Rigid if/then logic
- Fixed handoff sequences
- Predetermined paths

**Example:**
```
# Good (model-driven)
Agent prompt: "If the lead is qualified and ready to book, hand off to 
               SchedulerAgent. If qualified but not ready, continue 
               conversation to understand their needs."

# Bad (hardcoded)
if lead.score >= 7:
    handoff_to_scheduler()
else:
    send_decline()
```

### **2. Shared Context Management**

**What to share:**
- Customer information (name, contact, preferences)
- Interaction history (what was discussed)
- Business context (pricing, availability, policies)
- Current state (where we are in workflow)

**What NOT to share:**
- Internal debugging info
- Sensitive credentials
- Unnecessary details

**Implementation:**
```
# Shared context structure
shared_context = {
    "customer": {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "555-1234"
    },
    "lead": {
        "service_needed": "HVAC repair",
        "urgency": "emergency",
        "budget": "$2000",
        "qualification_score": 9
    },
    "workflow_state": {
        "current_step": "scheduling",
        "completed_steps": ["qualification"],
        "next_steps": ["booking", "invoicing"]
    }
}
```

### **3. Handoff Best Practices**

**Clear handoff instructions:**
```
# In Lead Response Agent prompt
"When you've qualified a lead, hand off to SchedulerAgent with this context:
- Customer name, email, phone
- Service needed
- Urgency level
- Budget range
- Any special requirements

Use: handoff_to_agent(target='SchedulerAgent', context={...})"
```

**Verify handoff success:**
- Log all handoffs
- Track: From agent, to agent, context passed
- Alert if handoff fails
- Retry logic if needed

### **4. Error Handling**

**Agent-level errors:**
- Agent fails to respond → Retry with same agent
- Agent gives invalid response → Reflexion (self-critique and retry)
- Agent stuck in loop → Timeout and escalate to human

**Tool-level errors:**
- Tool call fails → Retry 3 times with exponential backoff
- External API down → Use fallback (e.g., manual booking)
- Rate limit hit → Queue and retry later

**Handoff errors:**
- Target agent not available → Fallback to previous agent
- Context missing → Request missing info from user
- Infinite loop detected → Break and escalate to human

**Implementation:**
```
# In Swarm configuration
swarm = Swarm(
    agents=[lead_agent, scheduler_agent, invoice_agent],
    max_handoffs=10,  # Prevent infinite loops
    timeout=300,  # 5 minutes max per interaction
    error_handler=handle_swarm_error
)
```

---

## Tool Implementation Guidelines

### **Tool Structure**

**Every tool should:**
1. Have clear purpose (one thing well)
2. Have typed inputs/outputs (Pydantic models)
3. Have error handling (try/except)
4. Have logging (CloudWatch)
5. Have retry logic (for external APIs)
6. Have timeout (prevent hanging)

**Example Tool Structure:**
```
Tool: check_availability

Purpose: Check technician calendar availability

Inputs:
  - date_range: DateRange (start_date, end_date)
  - service_type: str (HVAC, plumbing, electrical)
  - location: str (zip code or address)

Outputs:
  - available_slots: List[TimeSlot]
  - technicians: List[Technician]

Error Handling:
  - Calendar API down → Return cached availability
  - No availability → Return empty list with message
  - Invalid date range → Return error with suggestion

Logging:
  - Log: Input parameters
  - Log: API calls made
  - Log: Results returned
  - Log: Errors encountered

Retry Logic:
  - Retry: 3 times with exponential backoff
  - Timeout: 10 seconds per attempt
  - Fallback: Manual booking notification
```

---

## Integration Best Practices

### **Gmail API**

**Authentication:**
- Use OAuth2 (not API keys)
- Store tokens in Secrets Manager
- Refresh tokens automatically
- Handle token expiration

**Rate Limits:**
- 250 quota units per user per second
- 1 billion quota units per day
- Monitor usage
- Implement backoff

**Best Practices:**
- Use push notifications (not polling)
- Watch specific labels only
- Batch operations when possible
- Cache frequently accessed data

### **Google Calendar API**

**Authentication:**
- OAuth2 with calendar scope
- Service account for backend access
- Store credentials securely

**Rate Limits:**
- 1,000,000 queries per day
- 10 queries per second per user
- Monitor and throttle

**Best Practices:**
- Use freebusy queries (faster)
- Batch availability checks
- Cache availability for 5 minutes
- Handle timezone correctly

### **Stripe API**

**Authentication:**
- API keys (secret key for backend)
- Webhook signing secrets
- Store in Secrets Manager

**Rate Limits:**
- 100 requests per second
- Burst up to 1,000
- Monitor usage

**Best Practices:**
- Use idempotency keys (prevent duplicates)
- Handle webhooks (payment.succeeded)
- Test in test mode first
- Implement retry logic

### **Twilio API**

**Authentication:**
- Account SID + Auth Token
- Store in Secrets Manager

**Rate Limits:**
- 1,000 messages per second
- Monitor usage

**Best Practices:**
- Use message queues (SQS)
- Handle delivery status
- Implement retry for failed messages
- Track costs (per message)

---

## Deployment Architecture

### **AgentCore Runtime**
- Hosts: All 3 agents in one container
- Scaling: Auto-scales based on load
- Memory: 2GB per container
- CPU: 2 vCPUs per container

### **AgentCore Gateway**
- Routes: Tool calls to Lambda functions
- Auth: OAuth2 token validation
- Tracking: Usage per org_id
- Rate limiting: 1,000 calls/hour per org

### **Lambda Functions**
- Runtime: Python 3.13
- Architecture: ARM64 (20% cost savings)
- Memory: 256-512 MB
- Timeout: 30-60 seconds
- Concurrency: 100 per function

### **DynamoDB Tables**
- Billing: Provisioned capacity (cost-optimized)
- Capacity: 1 RCU/WCU per table (auto-scaling enabled)
- Backup: Point-in-time recovery (35 days)
- Encryption: AWS-managed KMS keys

### **S3 Buckets**
- Purpose: Documents, invoices, logs
- Encryption: AES-256
- Lifecycle: Intelligent tiering
- Retention: 7 years (compliance)

---

## Testing Strategy

### **Unit Tests**
- Test each agent individually (mock tools)
- Test each tool individually (mock external APIs)
- Test handoff logic
- Test error handling

### **Integration Tests**
- Test agent-to-tool communication
- Test tool-to-database operations
- Test external API integrations
- Test handoffs between agents

### **End-to-End Tests**
- Test complete workflow (lead → schedule → invoice)
- Test error scenarios
- Test edge cases
- Test at scale (100+ concurrent)

### **Beta Testing**
- 3 friendly customers
- Monitor every interaction
- Collect feedback
- Fix issues immediately

---

## Success Metrics

**Performance:**
- Response time: < 60 seconds (first response)
- Qualification accuracy: > 80%
- Booking success rate: > 90%
- Invoice accuracy: > 95%

**Business:**
- Lead-to-appointment conversion: > 60%
- Appointment-to-payment conversion: > 80%
- Customer satisfaction: > 4.5/5
- Churn rate: < 5%/month

**Technical:**
- Uptime: > 99.9%
- Error rate: < 1%
- Handoff success rate: > 95%
- Tool call latency: < 500ms

---

## Ready to Build!

**You now have:**
- ✅ Complete agent specifications
- ✅ All tools defined (21 tools, 9 Lambda functions)
- ✅ Database schemas (4 tables)
- ✅ Model selection (Haiku for cost optimization)
- ✅ Swarm pattern implementation guide
- ✅ Memory management strategy
- ✅ Integration best practices
- ✅ Testing strategy
- ✅ Deployment architecture

**Start with Week 1: Build Lead Response Agent**

**Follow the checklist. Test thoroughly. Ship fast! 🚀**
