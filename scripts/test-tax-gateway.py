#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Test Tax Document Agent Gateway Tools.

Tests all 5 Gateway Lambda tools directly without going through the agent.

Usage:
    python scripts/test-tax-gateway.py
"""

import sys
import json
import requests
import boto3
from pathlib import Path

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, get_ssm_params, print_msg, print_section


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


def call_gateway_tool(gateway_url: str, access_token: str, tool_name: str, arguments: dict) -> dict:
    """Call a Gateway tool."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        'jsonrpc': '2.0',
        'id': f'test-{tool_name}',
        'method': 'tools/call',
        'params': {
            'name': tool_name,
            'arguments': arguments
        }
    }
    
    response = requests.post(gateway_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        print_msg(f"Gateway call failed: {response.status_code} - {response.text}", "error")
        return {'error': response.text}
    
    return response.json()


def list_gateway_tools(gateway_url: str, access_token: str) -> dict:
    """List all available Gateway tools."""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    payload = {
        'jsonrpc': '2.0',
        'id': 'list-tools',
        'method': 'tools/list'
    }
    
    response = requests.post(gateway_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        print_msg(f"Gateway call failed: {response.status_code}", "error")
        sys.exit(1)
    
    return response.json()


def get_test_client_id(dynamodb, clients_table: str, accountant_id: str) -> str:
    """Get a test client ID."""
    table = dynamodb.Table(clients_table)
    
    try:
        response = table.scan(
            FilterExpression='accountant_id = :aid',
            ExpressionAttributeValues={':aid': accountant_id},
            Limit=1
        )
        
        if response['Items']:
            return response['Items'][0]['client_id']
        
        print_msg("No test clients found. Run seed-tax-test-data.py first.", "error")
        sys.exit(1)
        
    except ClientError as e:
        print_msg(f"Error querying clients: {e}", "error")
        sys.exit(1)


def main():
    """Main entry point."""
    print_section("Tax Document Agent - Gateway Tools Test")
    
    # Get configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Get Gateway configuration
    print("Fetching Gateway configuration...")
    params = get_ssm_params(
        stack_name,
        'gateway_url',
        'machine_client_id',
        'cognito_provider'
    )
    
    client_secret = get_secret(f'/{stack_name}/machine_client_secret')
    
    gateway_url = params['gateway_url']
    client_id = params['machine_client_id']
    cognito_domain = params['cognito_provider']
    token_url = f'https://{cognito_domain}/oauth2/token'
    
    print_msg("Configuration fetched")
    
    # Authenticate
    print_section("Authentication")
    print("Fetching access token...")
    access_token = fetch_access_token(client_id, client_secret, token_url)
    print_msg("Access token obtained")
    
    # List tools
    print_section("List Available Tools")
    tools_response = list_gateway_tools(gateway_url, access_token)
    
    if 'result' in tools_response and 'tools' in tools_response['result']:
        tools = tools_response['result']['tools']
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  • {tool['name']}: {tool.get('description', 'No description')[:60]}...")
    
    # Get test client ID
    dynamodb = boto3.resource('dynamodb')
    tables = get_table_names(stack_name)
    accountant_id = 'acc_test_001'
    
    print_section("Getting Test Client")
    test_client_id = get_test_client_id(dynamodb, tables['clients'], accountant_id)
    print(f"Test client ID: {test_client_id}")
    
    # Test Tool 1: Check Client Documents
    print_section("Test 1: Check Client Documents")
    result = call_gateway_tool(
        gateway_url,
        access_token,
        'check_client_documents',
        {
            'client_id': test_client_id,
            'tax_year': 2024
        }
    )
    print("Result:")
    print(json.dumps(result, indent=2))
    
    # Test Tool 2: Get Client Status
    print_section("Test 2: Get Client Status")
    result = call_gateway_tool(
        gateway_url,
        access_token,
        'get_client_status',
        {
            'accountant_id': accountant_id,
            'filter': 'all'
        }
    )
    print("Result:")
    print(json.dumps(result, indent=2)[:500] + "...")
    
    # Test Tool 3: Update Document Requirements
    print_section("Test 3: Update Document Requirements")
    result = call_gateway_tool(
        gateway_url,
        access_token,
        'update_document_requirements',
        {
            'client_id': test_client_id,
            'tax_year': 2024,
            'operation': 'add',
            'documents': [
                {
                    'document_type': '1099-B',
                    'source': 'Broker XYZ',
                    'required': False
                }
            ]
        }
    )
    print("Result:")
    print(json.dumps(result, indent=2))
    
    print_section("Test Summary")
    print_msg("All Gateway tools tested successfully!", "success")
    print("\nNext steps:")
    print("  1. Review test results above")
    print("  2. Run: python scripts/test-tax-agent.py")


if __name__ == "__main__":
    main()
