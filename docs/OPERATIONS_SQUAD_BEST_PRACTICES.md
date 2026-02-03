# Operations Squad: Best Practices & Lessons Learned

**Source:** Tax-demo implementation + AWS best practices + Strands documentation  
**Purpose:** Avoid common pitfalls, build production-ready system

---

## Best Practices from Your Tax-Demo

### **What Worked Well (Keep Doing)**

**1. Multi-Tenant Data Isolation**
- Every DynamoDB table includes org_id
- All queries filter by org_id
- JWT tokens include org_id claim
- Lambda functions validate org_id

**Lesson:** This prevents data leaks and enables per-customer scaling.

**2. Provisioned DynamoDB Capacity**
- 96% cost savings vs on-demand
- Auto-scaling for bursts
- Predictable costs

**Lesson:** For predictable workloads, provisioned is much cheaper.

**3. ARM64 Lambda Architecture**
- 20% cost savings vs x86
- Better performance per dollar
- All tools use ARM64

**Lesson:** Always use ARM64 unless you have x86-specific dependencies.

**4. Prompt Caching**
- System prompts > 1,024 tokens
- 50-70% input token savings
- Massive cost reduction

**Lesson:** Make system prompts detailed (>1,024 tokens) to enable caching.

**5. AgentCore Gateway for Tools**
- Centralized tool routing
- OAuth2 authentication
- Usage tracking built-in
- Rate limiting automatic

**Lesson:** Don't call Lambda directly from agents. Use Gateway.

**6. Streaming Responses**
- Better user experience
- Perceived faster response
- Can show progress

**Lesson:** Always implement streaming for customer-facing agents.

---

### **What to Improve (Lessons Learned)**

**1. Tool Naming**
- Tax-demo: Tool names got too long (>64 chars)
- **Fix:** Keep tool names short (<30 chars)
- **Example:** `doc-check___check_documents` → `check_docs`

**2. Error Handling**
- Tax-demo: Some tools fail silently
- **Fix:** Always return explicit errors
- **Example:** Don't return empty list, return error with reason

**3. Testing**
- Tax-demo: Not enough integration tests
- **Fix:** Test every handoff, every tool, every edge case
- **Example:** Write tests before building features

**4. Monitoring**
- Tax-demo: Limited visibility into agent decisions
- **Fix:** Log every handoff, every tool call, every decision
- **Example:** Use X-Ray tracing for full visibility

**5. Documentation**
- Tax-demo: Some tools undocumented
- **Fix:** Document every tool, every agent, every flow
- **Example:** Write docs as you build, not after

---

## AWS Best Practices for Operations Squad

### **DynamoDB Design**

**1. Partition Key Selection**
- **Best:** Use high-cardinality keys (lead_id, appointment_id, invoice_id)
- **Avoid:** Low-cardinality keys (status, date)
- **Why:** Prevents hot partitions, enables scaling

**2. GSI Design**
- **Best:** Create GSIs for common query patterns
- **Example:** org_id-status-index for "show me all qualified leads"
- **Avoid:** Scanning entire table
- **Why:** GSIs are fast and cheap, scans are slow and expensive

**3. Attribute Naming**
- **Best:** Use descriptive names (customer_email, scheduled_time)
- **Avoid:** Abbreviations (cust_em, sched_tm)
- **Why:** Readability and maintainability

**4. Data Types**
- **Best:** Use appropriate types (number for amounts, string for IDs)
- **Avoid:** Storing numbers as strings
- **Why:** Enables sorting, filtering, calculations

**5. Provisioned Capacity**
- **Best:** Start with 1 RCU/WCU, enable auto-scaling
- **Monitor:** CloudWatch metrics for throttling
- **Scale:** Increase when utilization > 70%
- **Why:** 96% cost savings vs on-demand

---

### **Lambda Function Design**

**1. Single Responsibility**
- **Best:** One tool = one Lambda function
- **Example:** check_availability (not check_and_book)
- **Avoid:** Monolithic functions that do everything
- **Why:** Easier to test, debug, scale

**2. Idempotency**
- **Best:** Same input = same output (no side effects on retry)
- **Example:** Use idempotency keys for Stripe
- **Avoid:** Creating duplicate records on retry
- **Why:** Retries are common, duplicates are bad

**3. Timeout Configuration**
- **Best:** Set appropriate timeouts (30-60 seconds)
- **Monitor:** Execution duration
- **Optimize:** Reduce cold starts
- **Why:** Prevents hanging, reduces costs

**4. Memory Allocation**
- **Best:** Start with 256 MB, increase if needed
- **Monitor:** Memory usage in CloudWatch
- **Optimize:** Right-size based on actual usage
- **Why:** Over-provisioning wastes money

**5. Environment Variables**
- **Best:** Store config in env vars (table names, URLs)
- **Avoid:** Hardcoding values
- **Why:** Enables multi-environment deployment

**6. Error Handling**
- **Best:** Try/except with specific exceptions
- **Log:** All errors with context
- **Return:** Structured error responses
- **Why:** Enables debugging and recovery

---

### **API Integration Best Practices**

**1. Gmail API**
- **Best:** Use push notifications (not polling)
- **Implement:** Pub/Sub webhook
- **Avoid:** Polling every minute (expensive, slow)
- **Why:** Real-time, efficient, cheaper

**2. Google Calendar API**
- **Best:** Use freebusy queries (faster than full calendar)
- **Cache:** Availability for 5 minutes
- **Batch:** Multiple availability checks
- **Why:** Reduces API calls, faster response

**3. Stripe API**
- **Best:** Use webhooks for payment status
- **Implement:** payment.succeeded webhook
- **Avoid:** Polling payment status
- **Why:** Real-time, reliable, efficient

**4. Twilio API**
- **Best:** Use message queues (SQS) for sending
- **Implement:** Async sending with status tracking
- **Avoid:** Synchronous sending (blocks)
- **Why:** Faster, more reliable, handles failures

**5. Rate Limiting**
- **Best:** Implement exponential backoff
- **Monitor:** API usage and limits
- **Cache:** Frequently accessed data
- **Why:** Prevents API bans, reduces costs

---

## Swarm Pattern Best Practices

### **1. Handoff Decision Logic**

**Best Practice: Let the model decide**
```
Agent prompt: "After qualifying the lead, decide:
- If qualified (score ≥ 7) AND ready to book → Hand off to SchedulerAgent
- If qualified (score ≥ 7) BUT not ready → Continue conversation
- If not qualified (score < 7) → Politely decline

Use handoff_to_agent tool when ready."
```

**Avoid: Hardcoded logic**
```
# Don't do this in code
if score >= 7:
    handoff_to_scheduler()
```

**Why:** Model-driven is more flexible and handles edge cases better.

---

### **2. Context Passing**

**Best Practice: Pass complete context**
```
handoff_to_agent(
    target="SchedulerAgent",
    context={
        "customer": {
            "name": "John Smith",
            "email": "john@example.com",
            "phone": "555-1234"
        },
        "lead": {
            "service_needed": "HVAC repair",
            "urgency": "emergency",
            "budget": "$2000",
            "location": "123 Main St",
            "qualification_score": 9
        },
        "conversation_summary": "Customer has emergency HVAC issue, 
                                 needs same-day service, budget is flexible"
    }
)
```

**Avoid: Minimal context**
```
handoff_to_agent(
    target="SchedulerAgent",
    context={"lead_id": "lead_123"}
)
```

**Why:** Next agent needs full context to continue seamlessly.

---

### **3. Shared Memory Access**

**Best Practice: Use all four memory layers**
```
# Agent checks all layers before responding
user_prefs = memory.get_user_preferences(org_id)
semantic_context = memory.search_semantic(query="John Smith history")
session_summary = memory.get_session_summary(session_id)
past_issues = memory.query_issues(similar_to=current_situation)

# Agent uses all context to make informed decision
```

**Avoid: Only using session memory**
```
# Don't ignore other memory layers
session_summary = memory.get_session_summary(session_id)
# Missing: user preferences, semantic context, past issues
```

**Why:** More context = better decisions = better customer experience.

---

### **4. Handoff Limits**

**Best Practice: Set max handoffs**
```
swarm = Swarm(
    agents=[lead_agent, scheduler_agent, invoice_agent],
    max_handoffs=10,  # Prevent infinite loops
    timeout=300  # 5 minutes max
)
```

**Why:** Prevents infinite loops if agents keep handing off to each other.

---

### **5. Error Recovery**

**Best Practice: Graceful degradation**
```
Agent prompt: "If you encounter an error:
1. Try the operation again (once)
2. If still fails, explain to customer what happened
3. Offer alternative (manual booking, call back)
4. Log the issue for human review
5. Never leave customer hanging"
```

**Avoid: Silent failures**
```
# Don't do this
try:
    book_appointment()
except:
    pass  # Customer never knows what happened
```

**Why:** Customers need to know what's happening, even if there's an error.

---

## Security Best Practices

### **1. Multi-Tenant Isolation**

**Best Practice: Enforce at every layer**
```
# Lambda function
def lambda_handler(event, context):
    # Extract org_id from JWT token
    org_id = event['requestContext']['authorizer']['org_id']
    
    # ALWAYS filter by org_id
    response = table.query(
        KeyConditionExpression='org_id = :org_id',
        ExpressionAttributeValues={':org_id': org_id}
    )
    
    # Never return data without org_id filter
```

**Avoid: Trusting client-provided org_id**
```
# Don't do this
org_id = json.loads(event['body'])['org_id']  # Can be spoofed!
```

**Why:** Prevents data leaks between customers.

---

### **2. Secrets Management**

**Best Practice: Use AWS Secrets Manager**
```
# Store in Secrets Manager
- Gmail OAuth tokens
- Stripe API keys
- Twilio credentials
- Calendar API tokens

# Retrieve in Lambda
import boto3
secrets = boto3.client('secretsmanager')
stripe_key = secrets.get_secret_value(SecretId='stripe_api_key')['SecretString']
```

**Avoid: Environment variables for secrets**
```
# Don't do this
STRIPE_KEY = os.environ['STRIPE_KEY']  # Visible in console
```

**Why:** Secrets Manager encrypts, rotates, and audits access.

---

### **3. Input Validation**

**Best Practice: Validate everything**
```
from pydantic import BaseModel, EmailStr, validator

class LeadInput(BaseModel):
    name: str
    email: EmailStr
    phone: str
    service_needed: str
    
    @validator('phone')
    def validate_phone(cls, v):
        # Validate phone format
        if not re.match(r'^\d{3}-\d{3}-\d{4}$', v):
            raise ValueError('Invalid phone format')
        return v
```

**Avoid: Trusting user input**
```
# Don't do this
name = request['name']  # Could be SQL injection, XSS, etc.
```

**Why:** Prevents injection attacks, data corruption.

---

## Performance Best Practices

### **1. Caching Strategy**

**What to cache:**
- Technician availability (5 minutes)
- Business settings (1 hour)
- Pricing rates (1 hour)
- Calendar availability (5 minutes)

**What NOT to cache:**
- Lead status (real-time)
- Appointment bookings (real-time)
- Payment status (real-time)

**Implementation:**
```
# Use ElastiCache Redis
import redis
cache = redis.Redis(host=redis_endpoint)

# Cache availability
cache.setex(
    key=f"availability:{technician_id}:{date}",
    time=300,  # 5 minutes
    value=json.dumps(available_slots)
)
```

**Why:** Reduces API calls, faster response, lower costs.

---

### **2. Database Query Optimization**

**Best Practice: Use GSIs for queries**
```
# Good: Use GSI
response = table.query(
    IndexName='org_id-status-index',
    KeyConditionExpression='org_id = :org AND status = :status',
    ExpressionAttributeValues={
        ':org': org_id,
        ':status': 'qualified'
    }
)

# Bad: Scan with filter
response = table.scan(
    FilterExpression='org_id = :org AND status = :status'
)
```

**Why:** Queries are 100x faster and cheaper than scans.

---

### **3. Batch Operations**

**Best Practice: Batch when possible**
```
# Good: Batch write
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)

# Bad: Individual writes
for item in items:
    table.put_item(Item=item)
```

**Why:** Reduces API calls, faster, cheaper.

---

## Cost Optimization Best Practices

### **1. Prompt Engineering for Cost**

**Best Practice: Be concise but complete**
```
# Good: Concise system prompt
"You are a Lead Response Agent. Respond to inquiries in 60 seconds, 
 qualify leads, hand off to Scheduler if qualified."

# Bad: Verbose system prompt
"You are an AI-powered Lead Response Agent designed to provide 
 exceptional customer service by responding to customer inquiries 
 in a timely manner, specifically within 60 seconds of receipt..."
```

**Why:** Shorter prompts = fewer tokens = lower costs.

**But:** Keep prompts > 1,024 tokens to enable caching (sweet spot: 1,200-1,500 tokens).

---

### **2. Model Selection**

**Best Practice: Use cheapest model that works**
```
# Lead qualification (simple): Nova Micro ($0.000035/1K)
# Lead response (medium): Haiku ($0.0008/1K)
# Complex reasoning (rare): Sonnet ($0.003/1K)
```

**Monitor:** Accuracy and customer satisfaction
**Upgrade:** Only if accuracy drops below 80%

**Why:** Haiku is 90% cheaper than Sonnet and works for 95% of cases.

---

### **3. Tool Call Optimization**

**Best Practice: Minimize tool calls**
```
# Good: One tool call with all data
result = check_availability_and_book(
    date_range=dates,
    service_type=service,
    customer=customer
)

# Bad: Multiple tool calls
availability = check_availability(dates)
technician = get_technician(service)
booking = book_appointment(availability, technician, customer)
```

**Why:** Each tool call costs money (Lambda invocation + Gateway routing).

---

## Reliability Best Practices

### **1. Retry Logic**

**Best Practice: Exponential backoff**
```
max_retries = 3
for attempt in range(max_retries):
    try:
        result = external_api_call()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        wait_time = 2 ** attempt  # 1s, 2s, 4s
        time.sleep(wait_time)
```

**Why:** Handles transient failures, doesn't overwhelm APIs.

---

### **2. Circuit Breaker**

**Best Practice: Fail fast when service is down**
```
if error_rate > 50% in last 5 minutes:
    # Stop calling failing service
    # Return cached data or error
    # Alert humans
    # Retry after 5 minutes
```

**Why:** Prevents cascading failures, saves money.

---

### **3. Graceful Degradation**

**Best Practice: Provide fallback**
```
# Try automated booking
try:
    book_appointment()
except CalendarAPIDown:
    # Fallback: Manual booking
    notify_human("Calendar API down, manual booking needed")
    send_customer("We'll call you to schedule within 1 hour")
```

**Why:** Customer still gets service, even if automation fails.

---

## Monitoring Best Practices

### **What to Monitor**

**Agent Performance:**
- Response time (p50, p95, p99)
- Accuracy rate (correct responses)
- Handoff success rate
- Error rate
- Token usage

**Tool Performance:**
- Execution time per tool
- Success rate per tool
- Error rate per tool
- API latency

**Business Metrics:**
- Leads processed
- Appointments booked
- Invoices sent
- Conversion rates
- Revenue impact

**Infrastructure:**
- Lambda invocations
- Lambda errors
- DynamoDB throttling
- S3 storage used
- Cost per customer

### **Alerting Thresholds**

**Critical (Page immediately):**
- Error rate > 10%
- Response time > 10 seconds
- Database throttling
- API endpoint down

**Warning (Email):**
- Error rate > 5%
- Response time > 5 seconds
- Daily cost > $100
- Integration failure

**Info (Dashboard):**
- New customer signup
- Milestone reached
- Performance improvement

---

## Testing Best Practices

### **1. Test Pyramid**

**Unit Tests (70%):**
- Test each tool individually
- Mock external APIs
- Test edge cases
- Fast, run on every commit

**Integration Tests (20%):**
- Test agent-to-tool communication
- Test tool-to-database
- Test handoffs
- Run before deployment

**End-to-End Tests (10%):**
- Test complete workflows
- Test with real integrations (staging)
- Test error scenarios
- Run before production deployment

---

### **2. Test Data**

**Best Practice: Realistic test data**
```
# Good: Realistic lead
{
    "name": "John Smith",
    "email": "john@example.com",
    "phone": "555-1234",
    "message": "My AC stopped working, need help today"
}

# Bad: Minimal test data
{
    "name": "Test",
    "email": "test@test.com"
}
```

**Why:** Realistic data catches real issues.

---

### **3. Beta Testing**

**Best Practice: 3 friendly customers**
- Offer: Free for 30 days
- Monitor: Every interaction
- Collect: Detailed feedback
- Fix: Issues within 24 hours

**Why:** Real usage reveals issues you can't anticipate.

---

## Documentation Best Practices

### **1. Tool Documentation**

**Best Practice: Document every tool**
```
Tool: check_availability

Purpose: Check technician calendar availability for booking

Inputs:
  - date_range: Start and end dates to check
  - service_type: Type of service (HVAC, plumbing, electrical)
  - location: Customer location (for proximity matching)

Outputs:
  - available_slots: List of available time slots
  - technicians: List of qualified technicians

Error Cases:
  - Calendar API down: Returns cached availability
  - No availability: Returns empty list with message
  - Invalid date range: Returns error

Example:
  Input: {date_range: "2026-02-03 to 2026-02-05", service_type: "HVAC"}
  Output: [{time: "2026-02-03 14:00", technician: "Mike Johnson"}]
```

---

### **2. Agent Documentation**

**Best Practice: Document behavior**
```
Agent: Lead Response Agent

Role: First point of contact for customer inquiries

Behavior:
  - Responds within 60 seconds
  - Asks qualifying questions
  - Scores leads 1-10
  - Hands off to Scheduler if score ≥ 7

Handoff Criteria:
  - Qualified: score ≥ 7, has contact info, in service area
  - Not qualified: score < 7, outside service area, not a real lead

Edge Cases:
  - Ambiguous service request: Ask clarifying questions
  - No contact info: Request email or phone
  - After hours: Still respond, schedule for next business day
```

---

### **3. Runbooks**

**Best Practice: Document common issues**
```
Issue: Agent not responding to emails

Diagnosis:
  1. Check Gmail API quota (CloudWatch)
  2. Check Lambda errors (CloudWatch Logs)
  3. Check Gateway connectivity
  4. Check agent deployment status

Resolution:
  1. If quota exceeded: Wait for reset or increase quota
  2. If Lambda error: Check logs, fix code, redeploy
  3. If Gateway down: Check AgentCore status
  4. If agent down: Redeploy agent

Prevention:
  - Monitor Gmail API usage
  - Set up alerts for quota warnings
  - Implement retry logic
```

---

## Deployment Best Practices

### **1. Blue-Green Deployment**

**Best Practice: Zero-downtime deployments**
```
1. Deploy new version (green)
2. Test green version
3. Switch traffic to green
4. Monitor for errors
5. Keep blue version for 24 hours (rollback if needed)
6. Delete blue version
```

**Why:** Can rollback instantly if issues found.

---

### **2. Configuration Management**

**Best Practice: Separate config from code**
```
# config.yaml
operations_squad:
  agents:
    lead_response:
      model: "claude-3-5-haiku"
      temperature: 0.1
      max_tokens: 1024
    scheduler:
      model: "claude-3-5-haiku"
      temperature: 0.0
      max_tokens: 512
  tools:
    email_monitoring:
      check_interval: 30  # seconds
    booking:
      buffer_minutes: 30
```

**Why:** Can change config without code changes.

---

### **3. Environment Strategy**

**Best Practice: Three environments**
- **Development:** Your local machine, test data
- **Staging:** AWS staging account, beta customers
- **Production:** AWS production account, paying customers

**Why:** Test thoroughly before production, isolate customer data.

---

## Summary: Top 10 Best Practices

1. ✅ **Multi-tenant isolation** - org_id everywhere
2. ✅ **Provisioned DynamoDB** - 96% cost savings
3. ✅ **ARM64 Lambda** - 20% cost savings
4. ✅ **Prompt caching** - 50-70% token savings
5. ✅ **Model-driven handoffs** - Let AI decide
6. ✅ **Four-layer memory** - Complete context
7. ✅ **Comprehensive error handling** - Never fail silently
8. ✅ **Extensive monitoring** - Know what's happening
9. ✅ **Thorough testing** - Unit, integration, e2e
10. ✅ **Clear documentation** - Tools, agents, runbooks

**Follow these and you'll build a production-ready, scalable, cost-effective Operations Squad! 🚀**
