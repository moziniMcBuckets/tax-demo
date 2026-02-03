# Local Testing Guide: Operations Squad

**Purpose:** Test agents locally before deploying to AWS  
**Authentication:** Two options (with Gateway vs without Gateway)

---

## Authentication Architecture

### **Production Flow (With Gateway):**

```
Agent → OAuth2 Token (Cognito) → Gateway → Lambda Tools → DynamoDB
```

**Authentication:**
1. Agent requests OAuth2 token from Cognito (client credentials flow)
2. Cognito validates client_id + client_secret
3. Cognito returns access_token
4. Agent calls Gateway with Bearer token
5. Gateway validates token
6. Gateway routes to Lambda tools

**Required:**
- Cognito User Pool (deployed)
- Machine-to-machine client (deployed)
- AgentCore Gateway (deployed)
- Client secret in Secrets Manager

---

### **Local Testing Flow (Without Gateway):**

```
Agent → Mock Tools (Local Python) → Local DynamoDB or Mock Data
```

**Authentication:**
- None needed (tools are local Python functions)
- No Cognito, no Gateway, no AWS
- Fast iteration, easy debugging

---

## Option 1: Local Testing Without Gateway (Recommended for Week 1)

### **Why This First:**
- ✅ No AWS deployment needed
- ✅ Fast iteration (no deploy cycle)
- ✅ Easy debugging
- ✅ No authentication complexity
- ✅ Test agent logic independently

### **Setup (30 minutes)**

**Step 1: Create Mock Tools**

**Create `tests/mock_tools.py`:**

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Mock tools for local testing (no AWS, no Gateway)
"""

from strands import tool
from typing import Dict, Any

# In-memory storage for testing
mock_leads = {}
mock_appointments = {}
mock_invoices = {}

@tool
def qualify_lead(
    name: str,
    email: str = None,
    phone: str = None,
    service_needed: str = None,
    urgency: str = "flexible",
    budget: str = None,
    location: str = None
) -> Dict[str, Any]:
    """
    Qualify and score a lead (MOCK VERSION).
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
        service_needed: Service requested
        urgency: Urgency level
        budget: Budget range
        location: Customer location
    
    Returns:
        Qualification result
    """
    # Simple scoring logic
    score = 0
    if email or phone:
        score += 3
    if service_needed:
        score += 2
    if urgency == 'emergency':
        score += 2
    if budget:
        score += 2
    if location:
        score += 1
    
    qualified = score >= 7
    lead_id = f"lead_{len(mock_leads) + 1}"
    
    # Store in mock database
    mock_leads[lead_id] = {
        'lead_id': lead_id,
        'name': name,
        'email': email,
        'phone': phone,
        'service_needed': service_needed,
        'urgency': urgency,
        'budget': budget,
        'location': location,
        'qualified': qualified,
        'score': score
    }
    
    print(f"[MOCK] Lead qualified: {lead_id}, score: {score}, qualified: {qualified}")
    
    return {
        'lead_id': lead_id,
        'qualified': qualified,
        'score': score,
        'reason': f'Score: {score}/10'
    }

@tool
def send_response(
    lead_id: str,
    message: str,
    contact_method: str = "email"
) -> Dict[str, Any]:
    """
    Send response to lead (MOCK VERSION).
    
    Args:
        lead_id: Lead identifier
        message: Message to send
        contact_method: How to contact (email or sms)
    
    Returns:
        Send status
    """
    if lead_id not in mock_leads:
        return {'error': 'Lead not found'}
    
    lead = mock_leads[lead_id]
    
    print(f"[MOCK] Sending {contact_method} to {lead['name']}")
    print(f"[MOCK] Message: {message}")
    
    return {
        'sent': True,
        'to': lead.get('email') or lead.get('phone'),
        'method': contact_method
    }

@tool
def check_availability(
    start_date: str,
    service_type: str,
    location: str = None
) -> Dict[str, Any]:
    """
    Check technician availability (MOCK VERSION).
    
    Args:
        start_date: Start date for availability
        service_type: Service type
        location: Customer location
    
    Returns:
        Available slots
    """
    # Mock availability
    available_slots = [
        {
            'time': f'{start_date} 14:00',
            'technician_id': 'tech_001',
            'technician_name': 'Mike Johnson',
            'skills': ['HVAC', 'plumbing']
        },
        {
            'time': f'{start_date} 16:00',
            'technician_id': 'tech_002',
            'technician_name': 'Sarah Lee',
            'skills': ['electrical', 'HVAC']
        }
    ]
    
    print(f"[MOCK] Found {len(available_slots)} available slots")
    
    return {
        'available_slots': available_slots,
        'count': len(available_slots)
    }

@tool
def book_appointment(
    lead_id: str,
    scheduled_time: str,
    technician_id: str,
    service_type: str,
    customer_address: str = None
) -> Dict[str, Any]:
    """
    Book appointment (MOCK VERSION).
    
    Args:
        lead_id: Lead identifier
        scheduled_time: Appointment time
        technician_id: Technician identifier
        service_type: Service type
        customer_address: Service location
    
    Returns:
        Appointment details
    """
    if lead_id not in mock_leads:
        return {'error': 'Lead not found'}
    
    lead = mock_leads[lead_id]
    appointment_id = f"appt_{len(mock_appointments) + 1}"
    
    # Store in mock database
    mock_appointments[appointment_id] = {
        'appointment_id': appointment_id,
        'lead_id': lead_id,
        'customer_name': lead['name'],
        'scheduled_time': scheduled_time,
        'technician_id': technician_id,
        'service_type': service_type,
        'status': 'scheduled'
    }
    
    print(f"[MOCK] Appointment booked: {appointment_id}")
    print(f"[MOCK] Time: {scheduled_time}, Technician: {technician_id}")
    
    return {
        'appointment_id': appointment_id,
        'scheduled_time': scheduled_time,
        'status': 'scheduled'
    }

@tool
def send_confirmation(appointment_id: str) -> Dict[str, Any]:
    """
    Send appointment confirmation (MOCK VERSION).
    
    Args:
        appointment_id: Appointment identifier
    
    Returns:
        Confirmation status
    """
    if appointment_id not in mock_appointments:
        return {'error': 'Appointment not found'}
    
    appt = mock_appointments[appointment_id]
    
    print(f"[MOCK] Sending confirmation for {appointment_id}")
    print(f"[MOCK] To: {appt['customer_name']}")
    print(f"[MOCK] Time: {appt['scheduled_time']}")
    
    return {
        'sent': True,
        'appointment_id': appointment_id
    }

@tool
def generate_invoice(
    appointment_id: str,
    line_items: list,
    tax_rate: float = 0.08
) -> Dict[str, Any]:
    """
    Generate invoice (MOCK VERSION).
    
    Args:
        appointment_id: Appointment identifier
        line_items: Invoice line items
        tax_rate: Tax rate
    
    Returns:
        Invoice details
    """
    if appointment_id not in mock_appointments:
        return {'error': 'Appointment not found'}
    
    # Calculate totals
    subtotal = sum(item['amount'] for item in line_items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    
    invoice_id = f"inv_{len(mock_invoices) + 1}"
    
    # Store in mock database
    mock_invoices[invoice_id] = {
        'invoice_id': invoice_id,
        'appointment_id': appointment_id,
        'line_items': line_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'status': 'draft'
    }
    
    print(f"[MOCK] Invoice generated: {invoice_id}")
    print(f"[MOCK] Total: ${total:.2f}")
    
    return {
        'invoice_id': invoice_id,
        'total': total,
        'status': 'draft'
    }
```

**Step 2: Create Local Test Agent**

**Create `tests/test_local_agent.py`:**

```python
#!/usr/bin/env python3

"""
Test Operations Squad locally (no AWS, no Gateway)
"""

import asyncio
from strands import Agent, Swarm
from strands.models import BedrockModel
from mock_tools import (
    qualify_lead,
    send_response,
    check_availability,
    book_appointment,
    send_confirmation,
    generate_invoice
)

def create_local_operations_squad():
    """Create Operations Squad with mock tools."""
    
    # Lead Response Agent
    lead_agent = Agent(
        name="LeadResponseAgent",
        system_prompt="""You are a Lead Response Agent.

Respond to inquiries, qualify leads, hand off to Scheduler if qualified.

Use these tools:
- qualify_lead: Score and qualify leads
- send_response: Send response to customer

If qualified (score ≥ 7), say: "Handing off to SchedulerAgent" """,
        tools=[qualify_lead, send_response],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.1
        )
    )
    
    # Scheduler Agent
    scheduler_agent = Agent(
        name="SchedulerAgent",
        system_prompt="""You are an Appointment Scheduler Agent.

Book appointments for qualified leads.

Use these tools:
- check_availability: Find available time slots
- book_appointment: Book the appointment
- send_confirmation: Send confirmation

After booking, say: "Handing off to InvoiceAgent" """,
        tools=[check_availability, book_appointment, send_confirmation],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.0
        )
    )
    
    # Invoice Agent
    invoice_agent = Agent(
        name="InvoiceAgent",
        system_prompt="""You are an Invoice Collection Agent.

Prepare invoices after appointments.

Use these tools:
- generate_invoice: Create invoice

After generating invoice, say: "Invoice prepared" """,
        tools=[generate_invoice],
        model=BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.0
        )
    )
    
    # Create Swarm
    squad = Swarm(
        agents=[lead_agent, scheduler_agent, invoice_agent],
        initial_agent=lead_agent
    )
    
    return squad

async def test_operations_squad():
    """Test complete Operations Squad flow."""
    
    print("="*60)
    print("Testing Vela Operations Squad (Local)")
    print("="*60)
    
    # Create squad
    squad = create_local_operations_squad()
    
    # Test query
    query = """
    New lead inquiry:
    Name: John Smith
    Email: john@example.com
    Phone: 555-1234
    Message: My AC stopped working, need help today. Budget is $2000.
    Location: 123 Main St, Anytown 12345
    """
    
    print(f"\nInput: {query}\n")
    print("Agent Responses:")
    print("-"*60)
    
    # Run squad
    async for event in squad.stream_async(query):
        if hasattr(event, 'content'):
            print(event.content)
        else:
            print(event)
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)

if __name__ == '__main__':
    asyncio.run(test_operations_squad())
```

**Step 3: Run Local Test**

```bash
# Install dependencies
pip install strands-agents boto3

# Run test (no AWS needed!)
python3 tests/test_local_agent.py
```

**Expected output:**
```
Testing Vela Operations Squad (Local)
============================================================

Input: New lead inquiry...

Agent Responses:
------------------------------------------------------------
[MOCK] Lead qualified: lead_1, score: 9, qualified: True
LeadResponseAgent: Hi John! I see you need emergency AC repair...
LeadResponseAgent: Handing off to SchedulerAgent

[MOCK] Found 2 available slots
SchedulerAgent: I found availability today at 2pm and 4pm...
[MOCK] Appointment booked: appt_1
SchedulerAgent: Appointment booked for today at 2pm with Mike Johnson
[MOCK] Sending confirmation for appt_1
SchedulerAgent: Confirmation sent. Handing off to InvoiceAgent

[MOCK] Invoice generated: inv_1
InvoiceAgent: Invoice prepared (draft). Will send after service completion.

============================================================
✅ Test Complete!
============================================================
```

---

## Option 2: Local Testing With Gateway (Week 2+)

### **Why This Later:**
- Requires AWS deployment
- Requires Cognito setup
- Requires Gateway deployment
- More complex but tests real flow

### **Setup (After deploying to AWS)**

**Step 1: Get Credentials from AWS**

```bash
# Get Cognito domain
aws ssm get-parameter \
  --name "/vela-ops-squad/cognito_provider" \
  --query 'Parameter.Value' \
  --output text

# Get client ID
aws ssm get-parameter \
  --name "/vela-ops-squad/machine_client_id" \
  --query 'Parameter.Value' \
  --output text

# Get client secret
aws secretsmanager get-secret-value \
  --secret-id "/vela-ops-squad/machine_client_secret" \
  --query 'SecretString' \
  --output text

# Get Gateway URL
aws ssm get-parameter \
  --name "/vela-ops-squad/gateway_url" \
  --query 'Parameter.Value' \
  --output text
```

**Step 2: Set Environment Variables**

```bash
export STACK_NAME="vela-ops-squad"
export AWS_REGION="us-west-2"
export AWS_DEFAULT_REGION="us-west-2"
export MEMORY_ID="mem_abc123xyz"  # From deployment logs
```

**Step 3: Test With Real Gateway**

**Create `tests/test_with_gateway.py`:**

```python
#!/usr/bin/env python3

"""
Test Operations Squad with real Gateway (requires AWS deployment)
"""

import asyncio
import os
from operations_squad import create_operations_squad

async def test_with_gateway():
    """Test with real Gateway and tools."""
    
    print("Testing with real Gateway...")
    
    # Create squad (will use real Gateway)
    squad = create_operations_squad(
        user_id='test_org_001',
        session_id='test_session_001'
    )
    
    # Test query
    query = "New lead: John Smith, john@example.com, needs HVAC repair urgently"
    
    print(f"Query: {query}\n")
    
    # Run squad
    async for event in squad.stream_async(query):
        print(event)
    
    print("\n✅ Test complete!")

if __name__ == '__main__':
    asyncio.run(test_with_gateway())
```

**Run test:**

```bash
python3 tests/test_with_gateway.py
```

**This will:**
- Get OAuth2 token from Cognito
- Call real Gateway
- Execute real Lambda tools
- Store in real DynamoDB

---

## Recommended Testing Strategy

### **Week 1: Local Testing Only**
- Use mock tools
- Test agent logic
- Test handoffs
- Fast iteration
- No AWS costs

### **Week 2: Hybrid Testing**
- Local agent with mock tools (fast iteration)
- Deploy tools to AWS (test integrations)
- Test Gateway authentication
- Verify real tools work

### **Week 3: Full Integration Testing**
- Deploy everything to AWS
- Test with real Gateway
- Test end-to-end flow
- Test with beta customers

### **Week 4: Production Testing**
- Deploy to production
- Test with real customers
- Monitor everything
- Fix issues immediately

---

## Authentication for Local Testing

### **Option 1: No Authentication (Mock Tools)**

**Pros:**
- ✅ Simple, fast
- ✅ No AWS needed
- ✅ Easy debugging

**Cons:**
- ⚠️ Doesn't test real integrations
- ⚠️ Doesn't test Gateway auth

**Use for:** Week 1, agent logic testing

---

### **Option 2: OAuth2 with Gateway (Real)**

**Pros:**
- ✅ Tests real flow
- ✅ Tests integrations
- ✅ Tests authentication

**Cons:**
- ⚠️ Requires AWS deployment
- ⚠️ Slower iteration
- ⚠️ More complex

**Use for:** Week 2+, integration testing

---

## Quick Start for Local Testing

**Today (15 minutes):**

```bash
# 1. Create test directory
mkdir tests
cd tests

# 2. Copy mock_tools.py (from above)
# 3. Copy test_local_agent.py (from above)

# 4. Install dependencies
pip install strands-agents

# 5. Run test
python3 test_local_agent.py
```

**You should see:**
- Agent responding to lead
- Lead qualified
- Handoff to Scheduler
- Appointment booked
- Handoff to Invoice
- Invoice prepared

**All without AWS! Perfect for Week 1 development! 🚀**

---

## Summary

**For local testing:**
- **Week 1:** Use mock tools (no authentication needed)
- **Week 2+:** Use real Gateway (OAuth2 with Cognito)

**Authentication used:**
- **Production:** OAuth2 Client Credentials flow (Cognito)
- **Local testing:** None (mock tools) or OAuth2 (real Gateway)

**Start with mock tools. It's faster and easier. Deploy to AWS when ready to test integrations.**

**Want me to create the mock tools file for you to start testing today?**
