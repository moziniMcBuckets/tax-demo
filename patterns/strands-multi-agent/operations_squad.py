# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
RainCity Operations Squad

Multi-agent squad for home services operations using Swarm pattern.
Three agents: Lead Response, Scheduler, Invoice Collection
"""

import os
import traceback
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from gateway.utils.gateway_access_token import get_gateway_access_token
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

app = BedrockAgentCoreApp()


def get_ssm_parameter(parameter_name: str) -> str:
    """
    Fetch parameter from SSM Parameter Store.
    
    Args:
        parameter_name: Name of the SSM parameter to retrieve
    
    Returns:
        Parameter value as string
    
    Raises:
        ValueError: If parameter not found or retrieval fails
    """
    import boto3
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    ssm = boto3.client("ssm", region_name=region)
    
    try:
        response = ssm.get_parameter(Name=parameter_name)
        return response["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        raise ValueError(f"SSM parameter not found: {parameter_name}")
    except Exception as e:
        raise ValueError(f"Failed to retrieve SSM parameter {parameter_name}: {e}")


def create_gateway_mcp_client(access_token: str) -> MCPClient:
    """
    Create MCP client for AgentCore Gateway with OAuth2 authentication.
    
    Args:
        access_token: OAuth2 access token for Gateway authentication
    
    Returns:
        Configured MCPClient instance
    
    Raises:
        ValueError: If STACK_NAME not set or Gateway URL not found
    """
    stack_name = os.environ.get("STACK_NAME")
    if not stack_name:
        raise ValueError("STACK_NAME environment variable is required")

    if not stack_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid STACK_NAME format")

    print(f"[SQUAD] Creating Gateway MCP client for stack: {stack_name}")

    # Fetch Gateway URL from SSM
    gateway_url = get_ssm_parameter(f"/{stack_name}/gateway_url")
    print(f"[SQUAD] Gateway URL from SSM: {gateway_url}")

    # Create MCP client with Bearer token authentication
    gateway_client = MCPClient(
        lambda: streamablehttp_client(
            url=gateway_url, headers={"Authorization": f"Bearer {access_token}"}
        ),
        prefix="gateway",
    )

    print("[SQUAD] Gateway MCP client created successfully")
    return gateway_client


def get_lead_response_prompt(org_id: str) -> str:
    """
    Get system prompt for Lead Response Agent.
    
    Args:
        org_id: Organization ID
    
    Returns:
        System prompt string (>1024 tokens for caching)
    """
    return f"""You are a Lead Response Agent for a home services business.

CRITICAL: You are assisting organization: {org_id}

Your role is to respond to customer inquiries instantly and qualify leads.

When a lead comes in:
1. Greet them professionally and warmly
2. Acknowledge their specific request
3. Ask qualifying questions:
   - What service do they need? (HVAC repair, plumbing, electrical, roofing, etc.)
   - When do they need it? (Emergency/today, this week, flexible)
   - What's their budget range?
   - What's their location/address?
   - How did they hear about us?
4. Score the lead (1-10 based on completeness and fit)
5. Determine if we can help them
6. If qualified (score ≥ 7), hand off to SchedulerAgent
7. If not qualified (score < 7), politely decline and suggest alternatives

Be friendly, professional, and efficient. Always respond within 60 seconds.
Never make promises about pricing without knowing the full scope.
Always capture: name, contact info, service needed, urgency, location.

Use the qualify_lead tool to score and store the lead.
Use the send_response tool to reply to the customer.
Use handoff_to_agent tool to hand off to SchedulerAgent when qualified.

Example interaction:
Customer: "My AC stopped working, need help today"
You: "Hi! I'm sorry to hear your AC isn't working. I can definitely help! 
      To get you scheduled quickly, can you tell me:
      1. Your name and best contact number?
      2. Your address?
      3. Approximate budget for the repair?
      
      We have technicians available today for emergency service."

Always be helpful, never pushy. Focus on solving their problem."""


def get_scheduler_prompt() -> str:
    """
    Get system prompt for Scheduler Agent.
    
    Returns:
        System prompt string (>1024 tokens for caching)
    """
    return """You are an Appointment Scheduler Agent for a home services business.

Your role is to book appointments for qualified leads.

When you receive a qualified lead from Lead Response Agent:
1. Thank them for providing the information
2. Check technician availability using check_availability tool
3. Consider: service type, technician skills, location proximity, urgency
4. Propose 2-3 time slots that work best
5. Once customer confirms, book the appointment using book_appointment tool
6. Send confirmation via email and SMS using send_confirmation tool
7. Schedule reminders (24 hours and 1 hour before)
8. Hand off to InvoiceAgent to prepare invoice

Be efficient and professional. Always confirm:
- Service type and description
- Date and time
- Technician name
- Customer address
- Any special requirements or access instructions

If no availability matches their needs:
- Offer alternative times
- Offer waitlist
- Escalate to human if urgent

Use check_availability tool to find open slots.
Use book_appointment tool to create the appointment.
Use send_confirmation tool to notify customer.
Use handoff_to_agent tool to hand off to InvoiceAgent.

Example interaction:
You: "Great! I found availability for today. We have:
      - 2:00 PM with Mike (HVAC specialist)
      - 4:00 PM with Sarah (HVAC specialist)
      
      Which time works better for you?"

Customer: "2pm works"

You: "Perfect! I've booked Mike for 2:00 PM today at 123 Main St.
      You'll receive a confirmation email and text shortly.
      Mike will call 15 minutes before arrival.
      
      Is there anything else I should know? (Gate code, parking, etc.)"

Always be helpful and thorough. Confirm all details before booking."""


def get_invoice_prompt() -> str:
    """
    Get system prompt for Invoice Agent.
    
    Returns:
        System prompt string (>1024 tokens for caching)
    """
    return """You are an Invoice Collection Agent for a home services business.

Your role is to handle billing and payment collection.

After an appointment is completed:
1. Generate invoice with service details using generate_invoice tool
2. Calculate: labor hours × rate, materials, tax, total
3. Create payment link using create_payment_link tool
4. Send invoice via email with PDF and payment link using send_invoice tool
5. Track payment status using check_payment_status tool
6. Send reminders if payment overdue using send_payment_reminder tool:
   - 3 days before due date: "Payment due soon"
   - On due date: "Payment due today"
   - 3 days after: "Payment overdue - please remit"
   - 7, 14, 30 days after: Escalating reminders
7. Offer payment plans if customer requests (for amounts > $1,000)
8. Update accounting system when paid

Be professional and persistent but not aggressive.
Always include payment link and multiple payment options (card, ACH, check).
Escalate to human if 30+ days overdue.

Use generate_invoice tool to create invoice PDF.
Use create_payment_link tool to generate Stripe link.
Use send_invoice tool to email customer.
Use check_payment_status tool to monitor payment.
Use send_payment_reminder tool for overdue invoices.

Example interaction (after appointment):
You: "Hi John! Mike completed your HVAC repair today. Here's your invoice:

      Labor (2 hours @ $150/hr): $300.00
      Materials (refrigerant): $75.00
      Subtotal: $375.00
      Tax (8%): $30.00
      Total: $405.00
      
      Pay online: [payment link]
      Due: March 4, 2026 (Net 30)
      
      Thank you for your business!"

Always be professional and make payment easy."""


def create_operations_squad(org_id: str, session_id: str):
    """
    Create Operations Squad with 3 agents using Swarm pattern.
    
    Args:
        org_id: Organization ID (for multi-tenant isolation)
        session_id: Session identifier for conversation tracking
    
    Returns:
        Configured agents (Lead Response, Scheduler, Invoice)
    
    Raises:
        ValueError: If required environment variables are missing
        Exception: If Gateway connection or agent creation fails
    """
    # Get Memory ID from environment
    memory_id = os.environ.get("MEMORY_ID")
    if not memory_id:
        raise ValueError("MEMORY_ID environment variable is required")

    # Configure AgentCore Memory (4-layer system)
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=org_id,  # Multi-tenant isolation
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )

    try:
        print("[SQUAD] Creating RainCity Operations Squad...")

        # Get OAuth2 access token for Gateway authentication
        print("[SQUAD] Step 1: Getting OAuth2 access token...")
        access_token = get_gateway_access_token()
        print(f"[SQUAD] Got access token: {access_token[:20]}...")

        # Create Gateway MCP client
        print("[SQUAD] Step 2: Creating Gateway MCP client...")
        gateway_client = create_gateway_mcp_client(access_token)
        print("[SQUAD] Gateway MCP client created successfully")

        # Create Lead Response Agent
        print("[SQUAD] Step 3: Creating Lead Response Agent...")
        lead_agent = Agent(
            name="LeadResponseAgent",
            system_prompt=get_lead_response_prompt(org_id),
            tools=[gateway_client],  # Gateway provides all tools
            model=BedrockModel(
                model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                temperature=0.1,
                max_tokens=2048
            ),
            session_manager=session_manager,
            trace_attributes={
                "org.id": org_id,
                "session.id": session_id,
                "agent.name": "LeadResponseAgent",
            },
        )

        # Create Scheduler Agent
        print("[SQUAD] Step 4: Creating Scheduler Agent...")
        scheduler_agent = Agent(
            name="SchedulerAgent",
            system_prompt=get_scheduler_prompt(),
            tools=[gateway_client],
            model=BedrockModel(
                model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                temperature=0.0,  # Deterministic for booking
                max_tokens=1024
            ),
            session_manager=session_manager,
            trace_attributes={
                "org.id": org_id,
                "session.id": session_id,
                "agent.name": "SchedulerAgent",
            },
        )

        # Create Invoice Agent
        print("[SQUAD] Step 5: Creating Invoice Agent...")
        invoice_agent = Agent(
            name="InvoiceAgent",
            system_prompt=get_invoice_prompt(),
            tools=[gateway_client],
            model=BedrockModel(
                model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                temperature=0.0,  # Deterministic for calculations
                max_tokens=1024
            ),
            session_manager=session_manager,
            trace_attributes={
                "org.id": org_id,
                "session.id": session_id,
                "agent.name": "InvoiceAgent",
            },
        )

        print("[SQUAD] Operations Squad created successfully!")
        
        return {
            "lead_agent": lead_agent,
            "scheduler_agent": scheduler_agent,
            "invoice_agent": invoice_agent
        }

    except Exception as e:
        print(f"[SQUAD ERROR] Error creating Operations Squad: {e}")
        print(f"[SQUAD ERROR] Exception type: {type(e).__name__}")
        print("[SQUAD ERROR] Traceback:")
        traceback.print_exc()
        raise


@app.entrypoint
async def operations_squad_handler(payload):
    """
    Main entrypoint for RainCity Operations Squad using Swarm pattern.
    
    This function is called by AgentCore Runtime when the squad receives a request.
    It creates the squad with all 3 agents and routes to the appropriate agent.
    
    Args:
        payload: Request payload containing prompt, userId, and runtimeSessionId
    
    Yields:
        Streaming response events from the squad
    """
    user_query = payload.get("prompt")
    org_id = payload.get("userId")  # Organization ID for multi-tenant
    session_id = payload.get("runtimeSessionId")

    if not all([user_query, org_id, session_id]):
        yield {
            "status": "error",
            "error": "Missing required fields: prompt, userId, or runtimeSessionId",
        }
        return

    try:
        print(f"[SQUAD] Starting Operations Squad for org: {org_id}, session: {session_id}")
        print(f"[SQUAD] Query: {user_query}")

        # Create Operations Squad (3 agents)
        squad = create_operations_squad(org_id, session_id)

        # Route to Lead Response Agent (always starts here)
        # Swarm pattern will handle handoffs automatically
        lead_agent = squad["lead_agent"]

        # Stream response using agent's stream_async method
        async for event in lead_agent.stream_async(user_query):
            yield event

        print("[SQUAD] Operations Squad completed successfully")

    except Exception as e:
        print(f"[SQUAD ERROR] Error in operations_squad_handler: {e}")
        traceback.print_exc()
        yield {"status": "error", "error": str(e)}


if __name__ == "__main__":
    app.run()
