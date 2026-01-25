#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Test Tax Document Agent end-to-end.

Tests the complete agent workflow including Gateway tools, memory, and streaming.

Usage:
    python scripts/test-tax-agent.py
"""

import sys
import json
import uuid
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, get_ssm_params, authenticate_cognito, print_msg, print_section


def invoke_agent(runtime_arn: str, prompt: str, session_id: str, user_id: str) -> dict:
    """
    Invoke AgentCore Runtime with a prompt.
    
    Args:
        runtime_arn: ARN of the AgentCore Runtime
        prompt: User query/prompt
        session_id: Session identifier
        user_id: User identifier
    
    Returns:
        Agent response dictionary
    """
    client = boto3.client('bedrock-agentcore')
    
    try:
        response = client.invoke_runtime(
            runtimeArn=runtime_arn,
            inputText=prompt,
            sessionId=session_id,
            userId=user_id,
        )
        
        # Parse response
        output = response.get('output', '')
        
        return {
            'success': True,
            'output': output,
            'session_id': session_id,
        }
        
    except ClientError as e:
        print_msg(f"Error invoking runtime: {e}", "error")
        return {
            'success': False,
            'error': str(e)
        }


def test_agent_query(runtime_arn: str, query: str, session_id: str, user_id: str) -> None:
    """Test a single agent query."""
    print(f"\n📝 Query: {query}")
    print("Invoking agent...")
    
    result = invoke_agent(runtime_arn, query, session_id, user_id)
    
    if result['success']:
        print_msg("Agent responded successfully", "success")
        print("\n💬 Response:")
        print(result['output'])
    else:
        print_msg(f"Agent error: {result['error']}", "error")


def main():
    """Main entry point."""
    print_section("Tax Document Agent - End-to-End Test")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Get Runtime ARN
    print("Fetching Runtime ARN...")
    params = get_ssm_params(stack_name, 'runtime-arn')
    runtime_arn = params['runtime-arn']
    print_msg(f"Runtime ARN: {runtime_arn}")
    
    # Generate session and user IDs
    session_id = f"test-session-{uuid.uuid4()}"
    user_id = "acc_test_001"  # Match accountant ID from seed data
    
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    
    # Test queries
    print_section("Test 1: Status Check")
    test_agent_query(
        runtime_arn,
        "Show me the status of all my clients",
        session_id,
        user_id
    )
    
    print_section("Test 2: Specific Client Query")
    test_agent_query(
        runtime_arn,
        "What documents are missing for John Smith?",
        session_id,
        user_id
    )
    
    print_section("Test 3: At-Risk Clients")
    test_agent_query(
        runtime_arn,
        "Which clients are at risk of missing the deadline?",
        session_id,
        user_id
    )
    
    print_section("Test 4: Tool Capabilities")
    test_agent_query(
        runtime_arn,
        "What tools do you have access to?",
        session_id,
        user_id
    )
    
    print_section("Test 5: Memory Test")
    test_agent_query(
        runtime_arn,
        "What did I ask you about in my first question?",
        session_id,
        user_id
    )
    
    print_section("Test Summary")
    print_msg("All agent tests completed!", "success")
    print("\nNext steps:")
    print("  1. Review agent responses above")
    print("  2. Test in frontend application")
    print("  3. Monitor CloudWatch logs")
    print("  4. Check cost dashboard")


if __name__ == "__main__":
    main()
