#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Comprehensive Gateway Tools Test Script

Tests all 6 tax Gateway tools and generates a detailed report.
"""

import sys
import json
import requests
from pathlib import Path
import boto3

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
        return {'error': f'HTTP {response.status_code}: {response.text}'}
    
    return response.json()


def test_tool(name: str, gateway_url: str, access_token: str, tool_name: str, arguments: dict) -> dict:
    """Test a single tool and return results."""
    print(f"\n🧪 Testing: {name}")
    print(f"   Tool: {tool_name}")
    print(f"   Args: {json.dumps(arguments, indent=10)[:100]}...")
    
    result = call_gateway_tool(gateway_url, access_token, tool_name, arguments)
    
    if 'error' in result:
        print_msg(f"   ❌ FAILED: {result['error']}", "error")
        return {'status': 'failed', 'error': result['error']}
    
    if 'result' in result and 'content' in result['result']:
        content = result['result']['content'][0]['text']
        is_error = result['result'].get('isError', False)
        
        if is_error:
            print_msg(f"   ❌ FAILED: {content[:100]}...", "error")
            return {'status': 'failed', 'error': content}
        else:
            print_msg(f"   ✅ SUCCESS", "success")
            return {'status': 'success', 'result': content}
    
    print_msg(f"   ⚠️  UNKNOWN RESPONSE", "warning")
    return {'status': 'unknown', 'result': result}


def main():
    """Main entry point."""
    print_section("Comprehensive Gateway Tools Test")
    
    # Get configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Authenticate
    print("Fetching Gateway configuration...")
    params = get_ssm_params(stack_name, 'gateway_url', 'machine_client_id', 'cognito_provider')
    client_secret = get_secret(f'/{stack_name}/machine_client_secret')
    
    gateway_url = params['gateway_url']
    client_id = params['machine_client_id']
    cognito_domain = params['cognito_provider']
    token_url = f'https://{cognito_domain}/oauth2/token'
    
    print_msg("Configuration fetched")
    
    print("\nAuthenticating...")
    access_token = fetch_access_token(client_id, client_secret, token_url)
    print_msg("Access token obtained")
    
    # Get test client ID
    dynamodb = boto3.resource('dynamodb')
    clients_table = dynamodb.Table(f'{stack_name}-clients')
    response = clients_table.scan(Limit=1)
    test_client_id = response['Items'][0]['client_id'] if response['Items'] else None
    
    if not test_client_id:
        print_msg("No test clients found. Run seed-tax-test-data.py first.", "error")
        sys.exit(1)
    
    print(f"\nTest Client ID: {test_client_id}")
    
    # Test all 6 tools
    print_section("Testing All Gateway Tools")
    
    results = []
    
    # Tool 1: Document Checker
    results.append(test_tool(
        "Document Checker",
        gateway_url,
        access_token,
        'document-checker-target___check_client_documents',
        {'client_id': test_client_id, 'tax_year': 2024}
    ))
    
    # Tool 2: Status Tracker
    results.append(test_tool(
        "Status Tracker",
        gateway_url,
        access_token,
        'status-tracker-target___get_client_status',
        {'accountant_id': 'acc_test_001', 'filter': 'all'}
    ))
    
    # Tool 3: Requirement Manager
    results.append(test_tool(
        "Requirement Manager",
        gateway_url,
        access_token,
        'requirement-manager-target___update_document_requirements',
        {
            'client_id': test_client_id,
            'tax_year': 2024,
            'operation': 'add',
            'documents': [{'document_type': 'Test Document', 'source': 'Test', 'required': False}]
        }
    ))
    
    # Tool 4: Email Sender
    results.append(test_tool(
        "Email Sender",
        gateway_url,
        access_token,
        'email-sender-target___send_followup_email',
        {
            'client_id': test_client_id,
            'missing_documents': ['W-2', '1099-INT'],
            'followup_number': 1,
            'custom_message': 'This is a test email from the automated system.'
        }
    ))
    
    # Tool 5: Escalation Manager
    results.append(test_tool(
        "Escalation Manager",
        gateway_url,
        access_token,
        'escalation-manager-target___escalate_client',
        {
            'client_id': test_client_id,
            'reason': 'Test escalation - no action needed',
            'notify_accountant': False  # Don't send notification during test
        }
    ))
    
    # Tool 6: Upload Manager
    results.append(test_tool(
        "Upload Manager",
        gateway_url,
        access_token,
        'upload-manager-target___generate_upload_url',
        {
            'client_id': test_client_id,
            'upload_token': 'test_token_123',
            'filename': 'test.pdf',
            'tax_year': 2024,
            'document_type': 'W-2'
        }
    ))
    
    # Generate Report
    print_section("Test Report")
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    
    print(f"\n📊 Results:")
    print(f"   ✅ Passed: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   ⏭️  Skipped: {skipped_count}")
    print(f"   📝 Total: {len(results)}")
    
    if failed_count == 0:
        print_msg("\n🎉 All testable tools passed!", "success")
    else:
        print_msg(f"\n⚠️  {failed_count} tool(s) failed", "warning")
    
    print("\n📋 Next Steps:")
    print("   1. Review any failures above")
    print("   2. Run: python3 scripts/test-tax-agent.py")
    print("   3. Open frontend: https://main.d3tseyzyms135a.amplifyapp.com")


if __name__ == "__main__":
    main()
