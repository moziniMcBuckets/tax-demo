# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tax Document Collection Agent

This agent helps accountants track client document submissions during tax season
and automates follow-up communications. It monitors client folders, sends personalized
reminders, and escalates unresponsive clients.
"""

import os
import traceback
import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from gateway.utils.gateway_access_token import get_gateway_access_token
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
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

    # Validate stack name format to prevent injection
    if not stack_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid STACK_NAME format")

    print(f"[AGENT] Creating Gateway MCP client for stack: {stack_name}")

    # Fetch Gateway URL from SSM
    gateway_url = get_ssm_parameter(f"/{stack_name}/gateway_url")
    print(f"[AGENT] Gateway URL from SSM: {gateway_url}")

    # Create MCP client with Bearer token authentication
    gateway_client = MCPClient(
        lambda: streamablehttp_client(
            url=gateway_url, headers={"Authorization": f"Bearer {access_token}"}
        ),
        prefix="gateway",
    )

    print("[AGENT] Gateway MCP client created successfully")
    return gateway_client


def get_model_for_task(task_type: str = "complex") -> BedrockModel:
    """
    Get appropriate model based on task complexity for cost optimization.
    
    Args:
        task_type: Type of task - 'complex' for reasoning, 'simple' for classification
    
    Returns:
        Configured BedrockModel instance
    """
    if task_type == "simple":
        # Use Nova Micro for simple classification tasks (ultra-low cost)
        return BedrockModel(
            model_id="us.amazon.nova-micro-v1:0",
            temperature=0
        )
    else:
        # Use Haiku for complex reasoning (90% cheaper than Sonnet)
        return BedrockModel(
            model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.1
        )


def create_tax_document_agent(user_id: str, session_id: str) -> Agent:
    """
    Create tax document collection agent with Gateway tools and memory.
    
    This agent specializes in tracking client document submissions, sending
    automated follow-ups, and escalating unresponsive clients. It has access
    to 5 Gateway tools for document checking, email sending, status tracking,
    escalation management, and requirement management.
    
    Args:
        user_id: Accountant user ID (actor_id for memory)
        session_id: Session identifier for conversation tracking
    
    Returns:
        Configured Agent instance with Gateway tools and memory
    
    Raises:
        ValueError: If required environment variables are missing
        Exception: If Gateway connection or agent creation fails
    """
    # Tax document agent system prompt (1,024+ tokens for prompt caching)
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
- W-2 (wage and tax statement from employers)
- 1099-INT (interest income from banks and financial institutions)
- 1099-DIV (dividend income from investment accounts)
- 1099-MISC (miscellaneous income from various sources)
- 1099-NEC (non-employee compensation for contractors and freelancers)
- 1099-B (broker transactions and securities sales)
- 1099-R (retirement account distributions)
- 1099-G (government payments including unemployment)
- 1099-K (payment card and third-party network transactions)
- Schedule K-1 (partnership and S-corporation income)
- Mortgage Interest Statement (Form 1098)
- Student Loan Interest (Form 1098-E)
- Tuition Statement (Form 1098-T)
- Health Insurance Forms (1095-A, 1095-B, 1095-C)
- Charitable donation receipts
- Medical expense receipts
- Business expense receipts
- Property tax statements
- Prior year tax returns
- Estimated tax payment records

**Follow-up protocol:**
- Reminder 1: Sent 3 days after initial request (friendly, informative)
- Reminder 2: Sent 7 days after Reminder 1 (more urgent, deadline mentioned)
- Reminder 3: Sent 14 days after Reminder 2 (urgent, potential penalties mentioned)
- Escalation: Flag for accountant call if no response 48 hours after Reminder 3

**Status categories:**
- Complete: All required documents received (100% completion)
- Incomplete: Some documents missing, follow-ups in progress (50-99% completion)
- At Risk: Multiple reminders sent, approaching escalation (0-49% completion or 2+ reminders)
- Escalated: Requires accountant intervention (3+ reminders with no response)

**Communication style:**
- Professional but friendly and approachable
- Specific about what documents are needed
- Include deadlines and consequences when relevant
- Personalize based on client name and specific missing items
- Use clear, jargon-free language

**When interacting with the accountant:**
- Provide clear, actionable summaries
- Highlight urgent cases first (escalated, then at risk)
- Suggest next steps based on client status
- Be concise but thorough
- Use data to support recommendations

**Important guidelines:**
- Always use your tools to check current status before making recommendations
- Never guess or assume document status - always verify with check_client_documents
- When sending reminders, always specify which documents are missing
- Track all follow-ups to maintain accurate history
- Escalate only when protocol thresholds are met
- Provide completion percentages to help accountants prioritize

**Example interactions:**

Accountant: "Show me the status of all my clients"
You: [Use get_client_status tool] "You have 50 clients. 15 complete (30%), 25 incomplete (50%), 8 at risk (16%), 2 escalated (4%). The 2 escalated clients are John Smith and Jane Doe - they need immediate phone calls."

Accountant: "What's missing for John Smith?"
You: [Use check_client_documents tool] "John Smith is at 33% complete. Missing: W-2 from Employer ABC, 1099-INT from Chase Bank. Last reminder sent 5 days ago (Reminder #2). Next reminder scheduled for tomorrow. Will escalate in 2 days if no response."

Accountant: "Send him a reminder now"
You: [Use send_followup_email tool] "Reminder #3 sent to john@example.com. Email includes specific list of missing documents and mentions potential filing delays. Next action: Escalate in 48 hours if no response."

Always be helpful, accurate, and proactive in assisting accountants with document collection."""

    # Use Haiku model for cost optimization (90% cheaper than Sonnet)
    bedrock_model = get_model_for_task("complex")

    # Get Memory ID from environment
    memory_id = os.environ.get("MEMORY_ID")
    if not memory_id:
        raise ValueError("MEMORY_ID environment variable is required")

    # Configure AgentCore Memory with 120-day expiration (tax season duration)
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=user_id,
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )

    try:
        print("[AGENT] Starting tax document agent creation with Gateway tools...")

        # Get OAuth2 access token for Gateway authentication
        print("[AGENT] Step 1: Getting OAuth2 access token...")
        access_token = get_gateway_access_token()
        print(f"[AGENT] Got access token: {access_token[:20]}...")

        # Create Gateway MCP client
        print("[AGENT] Step 2: Creating Gateway MCP client...")
        gateway_client = create_gateway_mcp_client(access_token)
        print("[AGENT] Gateway MCP client created successfully")

        print("[AGENT] Step 3: Creating Tax Document Agent with Gateway tools...")
        agent = Agent(
            name="TaxDocumentAgent",
            system_prompt=system_prompt,
            tools=[gateway_client],  # Gateway provides all 5 tools
            model=bedrock_model,
            session_manager=session_manager,
            trace_attributes={
                "user.id": user_id,
                "session.id": session_id,
                "agent.type": "tax_document_collection",
            },
        )
        print("[AGENT] Tax Document Agent created successfully with Gateway tools")
        return agent

    except Exception as e:
        print(f"[AGENT ERROR] Error creating Gateway client: {e}")
        print(f"[AGENT ERROR] Exception type: {type(e).__name__}")
        print("[AGENT ERROR] Traceback:")
        traceback.print_exc()
        print("[AGENT] Gateway connection failed - raising exception")
        raise


@app.entrypoint
async def agent_stream(payload):
    """
    Main entrypoint for the tax document agent using streaming.
    
    This function is called by AgentCore Runtime when the agent receives a request.
    It extracts the user's query, creates the agent with Gateway tools and memory,
    and streams the response back token-by-token.
    
    Args:
        payload: Request payload containing prompt, userId, and runtimeSessionId
    
    Yields:
        Streaming response events from the agent
    """
    user_query = payload.get("prompt")
    user_id = payload.get("userId")
    session_id = payload.get("runtimeSessionId")

    if not all([user_query, user_id, session_id]):
        yield {
            "status": "error",
            "error": "Missing required fields: prompt, userId, or runtimeSessionId",
        }
        return

    try:
        print(
            f"[STREAM] Starting streaming invocation for user: {user_id}, session: {session_id}"
        )
        print(f"[STREAM] Query: {user_query}")

        # Create tax document agent
        agent = create_tax_document_agent(user_id, session_id)

        # Stream response using agent's stream_async method
        async for event in agent.stream_async(user_query):
            yield event

        print("[STREAM] Streaming completed successfully")

    except Exception as e:
        print(f"[STREAM ERROR] Error in agent_stream: {e}")
        traceback.print_exc()
        yield {"status": "error", "error": str(e)}


if __name__ == "__main__":
    app.run()
