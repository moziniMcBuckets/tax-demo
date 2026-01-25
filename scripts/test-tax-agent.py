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


def invoke_agent(runtime_arn: str, prompt: str, session_id: str, user_id: str, access_token: str) -> dict:
    """
    Invoke AgentCore Runtime with a prompt using OAuth token.
    
    Args:
        runtime_arn: ARN of the AgentCore Runtime
        prompt: User query/prompt
        session_id: Session identifier (must be 33+ characters)
        user_id: User identifier
        access_token: Cognito access token for authentication
    
    Returns:
        Agent response dictionary
    """
    # Use requests library to call Runtime with OAuth token
    import requests
    
    # Extract runtime ID from ARN
    runtime_id = runtime_arn.split('/')[-1]
    runtime_url = f"https://{runtime_id}.bedrock-agentcore.us-west-2.amazonaws.com"
    
    try:
        payload_data = {"prompt": prompt}
        
        response = requests.post(
            runtime_url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Amz-Bedrock-AgentCore-Session-Id': session_id,
            },
            json=payload_data,
            timeout=60
        )
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}: {response.text}'
            }
        
        response_data = response.json()
        
        return {
            'success': True,
            'output': response_data,
            'session_id': session_id,
        }
        
    except Exception as e:
        print_msg(f"Error invoking runtime: {e}", "error")
        return {
            'success': False,
            'error': str(e)
        }


def test_agent_query(runtime_arn: str, query: str, session_id: str, user_id: str, access_token: str) -> None:
    """Test a single agent query."""
    print(f"\n📝 Query: {query}")
    print("Invoking agent...")
    
    result = invoke_agent(runtime_arn, query, session_id, user_id, access_token)
    
    if result['success']:
        print_msg("Agent responded successfully", "success")
        print("\n💬 Response:")
        print(json.dumps(result['output'], indent=2))
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
    
    # Get OAuth access token
    print("\nFetching OAuth access token...")
    gateway_params = get_ssm_params(stack_name, 'machine_client_id', 'cognito_provider')
    client_secret = get_secret(f'/{stack_name}/machine_client_secret')
    
    client_id = gateway_params['machine_client_id']
    cognito_domain = gateway_params['cognito_provider']
    token_url = f'https://{cognito_domain}/oauth2/token'
    
    access_token = fetch_access_token(client_id, client_secret, token_url)
    print_msg("Access token obtained")
    
    # Generate session and user IDs
    session_id = f"test-session-{uuid.uuid4()}"  # Must be 33+ characters
    user_id = "acc_test_001"
    
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    
    # Test queries
    print_section("Test 1: Status Check")
    test_agent_query(runtime_arn, "Show me the status of all my clients", session_id, user_id, access_token)
    
    print_section("Test 2: Specific Client Query")
    test_agent_query(runtime_arn, "What documents are missing for John Smith?", session_id, user_id, access_token)
    
    print_section("Test 3: At-Risk Clients")
    test_agent_query(runtime_arn, "Which clients are at risk of missing the deadline?", session_id, user_id, access_token)
    
    print_section("Test 4: Tool Capabilities")
    test_agent_query(runtime_arn, "What tools do you have access to?", session_id, user_id, access_token)
    
    print_section("Test 5: Memory Test")
    test_agent_query(runtime_arn, "What did I ask you about in my first question?", session_id, user_id, access_token)
    
    print_section("Test Summary")
    print_msg("All agent tests completed!", "success")
    print("\nNext steps:")
    print("  1. Review agent responses above")
    print("  2. Test in frontend application")
    print("  3. Monitor CloudWatch logs")
    print("  4. Check cost dashboard")


def get_secret(secret_name: str) -> str:
    """Fetch secret from AWS Secrets Manager."""
    secrets_client = boto3.client('secretsmanager')
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        raise RuntimeError(f"Error retrieving secret: {e}")


def fetch_access_token(client_id: str, client_secret: str, token_url: str) -> str:
    """Fetch OAuth2 access token."""
    import requests
    response = requests.post(
        token_url,
        data=f'grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    if response.status_code != 200:
        print_msg(f"Token request failed: {response.status_code}", "error")
        sys.exit(1)
    
    return response.json()['access_token']


if __name__ == "__main__":
    main()
