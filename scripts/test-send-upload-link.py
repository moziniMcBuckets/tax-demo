#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Test Send Upload Link Tool

Tests the send_upload_link Gateway tool by generating a token and sending
an email with the upload portal link to a test client.

Usage:
    python3 scripts/test-send-upload-link.py --client-id client_001
"""

import sys
import json
import argparse
from pathlib import Path
import requests

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import (
    get_stack_config,
    get_ssm_params,
    print_msg,
    print_section
)


def get_secret(secret_name: str) -> str:
    """
    Fetch secret from AWS Secrets Manager.
    
    Args:
        secret_name: Secret name or ARN
    
    Returns:
        Secret string value
    """
    secrets_client = boto3.client('secretsmanager')
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except Exception as e:
        print_msg(f"Error fetching secret: {e}", "error")
        raise


def fetch_access_token(client_id: str, client_secret: str, token_url: str) -> str:
    """Fetch OAuth2 access token for Gateway."""
    response = requests.post(
        token_url,
        data=f'grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to get access token: {response.text}")
    
    token_data = response.json()
    return token_data['access_token']


def test_send_upload_link(
    gateway_url: str,
    access_token: str,
    client_id: str,
    days_valid: int = 30,
    custom_message: str = None
):
    """Test the send_upload_link tool."""
    print_section(f"Testing Send Upload Link Tool for {client_id}")
    
    # Prepare request
    tool_name = "send-link-target___send_upload_link"
    
    payload = {
        "client_id": client_id,
        "days_valid": days_valid
    }
    
    if custom_message:
        payload["custom_message"] = custom_message
    
    print(f"Tool: {tool_name}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    # Call Gateway
    try:
        response = requests.post(
            f"{gateway_url}/tools/call",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "toolName": tool_name,
                "input": payload
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print_msg("✓ Upload link sent successfully!", "success")
            print(f"\nResponse:\n{json.dumps(result, indent=2)}")
            
            # Extract and display key information
            if 'content' in result and len(result['content']) > 0:
                content = json.loads(result['content'][0]['text'])
                if content.get('success'):
                    print_section("Upload Link Details")
                    print(f"Client: {content.get('client_name')} ({content.get('client_id')})")
                    print(f"Email sent to: {content.get('recipient')}")
                    print(f"Upload URL: {content.get('upload_url')}")
                    print(f"Valid until: {content.get('token_expires')}")
                    print(f"Days valid: {content.get('days_valid')}")
                    print(f"SES Message ID: {content.get('message_id')}")
                else:
                    print_msg(f"✗ Error: {content.get('error')}", "error")
        else:
            print_msg(f"✗ Failed: {response.text}", "error")
            
    except Exception as e:
        print_msg(f"✗ Exception: {str(e)}", "error")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test send upload link tool')
    parser.add_argument('--client-id', required=True, help='Client ID to send link to')
    parser.add_argument('--days', type=int, default=30, help='Days link is valid (default: 30)')
    parser.add_argument('--message', help='Custom message to include in email')
    
    args = parser.parse_args()
    
    print_section("Send Upload Link Tool Test")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Get Gateway configuration from SSM
    print("Fetching Gateway configuration from SSM...")
    params = get_ssm_params(stack_name, 'gateway_url', 'machine_client_id', 'cognito_provider')
    client_secret = get_secret(f'/{stack_name}/machine_client_secret')
    
    gateway_url = params['gateway_url']
    client_id = params['machine_client_id']
    cognito_domain = params['cognito_provider']
    token_url = f'https://{cognito_domain}/oauth2/token'
    
    print_msg("Configuration fetched", "success")
    print(f"Gateway URL: {gateway_url}")
    print(f"Client ID: {client_id[:20]}...")
    print(f"Token URL: {token_url}\n")
    
    # Get access token
    print("Fetching OAuth2 access token...")
    access_token = fetch_access_token(client_id, client_secret, token_url)
    print_msg("Access token obtained", "success")
    print(f"Token: {access_token[:20]}...\n")
    
    # Test send upload link
    test_send_upload_link(
        gateway_url=gateway_url,
        access_token=access_token,
        client_id=args.client_id,
        days_valid=args.days,
        custom_message=args.message
    )
    
    print_section("Test Complete")
    print_msg("Upload link tool test completed successfully!", "success")


if __name__ == "__main__":
    main()
