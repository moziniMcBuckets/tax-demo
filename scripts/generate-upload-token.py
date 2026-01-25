#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Generate Upload Token for Client

Creates a secure upload token for a client and updates their record in DynamoDB.
The token is used to authenticate client uploads via the upload portal.

Usage:
    python scripts/generate-upload-token.py --client-id <client_id>
"""

import sys
import secrets
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, print_msg, print_section


def generate_upload_token(client_id: str, stack_name: str, days_valid: int = 30) -> str:
    """
    Generate secure upload token for client.
    
    Args:
        client_id: Client identifier
        stack_name: Stack name for table lookup
        days_valid: Number of days token is valid
    
    Returns:
        Generated upload token
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(f'{stack_name}-clients')
    
    # Generate secure random token
    upload_token = secrets.token_urlsafe(32)
    token_expires = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    
    try:
        # Update client record with token
        table.update_item(
            Key={'client_id': client_id},
            UpdateExpression='SET upload_token = :token, token_expires = :expires',
            ExpressionAttributeValues={
                ':token': upload_token,
                ':expires': token_expires
            }
        )
        
        print_msg(f"Upload token generated for client {client_id}", "success")
        print(f"\nToken: {upload_token}")
        print(f"Expires: {token_expires[:10]}")
        
        return upload_token
        
    except ClientError as e:
        print_msg(f"Error updating client: {e}", "error")
        sys.exit(1)


def generate_upload_url(client_id: str, upload_token: str, api_url: str) -> str:
    """
    Generate upload portal URL for client.
    
    Args:
        client_id: Client identifier
        upload_token: Upload token
        api_url: API Gateway URL
    
    Returns:
        Complete upload portal URL
    """
    # In production, this would be your frontend URL
    frontend_url = "https://yourdomain.com"
    
    upload_url = f"{frontend_url}/upload?client={client_id}&token={upload_token}"
    
    return upload_url


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate upload token for client')
    parser.add_argument('--client-id', required=True, help='Client ID')
    parser.add_argument('--days', type=int, default=30, help='Days token is valid (default: 30)')
    
    args = parser.parse_args()
    
    print_section("Generate Client Upload Token")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}")
    print(f"Client ID: {args.client_id}\n")
    
    # Generate token
    upload_token = generate_upload_token(args.client_id, stack_name, args.days)
    
    # Generate upload URL
    upload_url = generate_upload_url(args.client_id, upload_token, "API_URL")
    
    print_section("Upload Portal URL")
    print(upload_url)
    
    print_section("Email Template")
    print(f"""
Dear Client,

Please upload your tax documents using this secure link:

{upload_url}

This link is valid for {args.days} days and is unique to you.

Required documents:
- W-2 from all employers
- 1099 forms from all sources
- Prior year tax return

If you have any questions, please contact your accountant.

Best regards,
Your Accountant
""")
    
    print_msg("\nToken generated successfully!", "success")


if __name__ == "__main__":
    main()
