#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Update Client Accountant IDs

Updates all clients with accountant_id 'acc_test_001' to use a real Cognito user ID.
This fixes the issue where seeded test data doesn't match the logged-in user.

Usage:
    python3 scripts/update-client-accountant-id.py NEW_ACCOUNTANT_ID
    
Example:
    python3 scripts/update-client-accountant-id.py e8a1f3a0-8001-70a0-3ed9-3d4b95fc7500
"""

import sys
import boto3

if len(sys.argv) < 2:
    print("Usage: python3 update-client-accountant-id.py NEW_ACCOUNTANT_ID")
    print("Example: python3 update-client-accountant-id.py e8a1f3a0-8001-70a0-3ed9-3d4b95fc7500")
    sys.exit(1)

new_accountant_id = sys.argv[1]

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('tax-agent-clients')

print(f"Updating clients to use accountant_id: {new_accountant_id}")
print()

# Scan for all clients with old accountant_id
response = table.scan(
    FilterExpression='accountant_id = :old_id',
    ExpressionAttributeValues={':old_id': 'acc_test_001'}
)

clients = response.get('Items', [])
print(f"Found {len(clients)} clients to update")
print()

# Update each client
for client in clients:
    client_id = client['client_id']
    client_name = client.get('client_name', 'Unknown')
    
    try:
        table.update_item(
            Key={'client_id': client_id},
            UpdateExpression='SET accountant_id = :new_id',
            ExpressionAttributeValues={':new_id': new_accountant_id}
        )
        print(f"✓ Updated {client_name} ({client_id})")
    except Exception as e:
        print(f"✗ Failed to update {client_name}: {e}")

print()
print(f"✓ All clients updated to accountant_id: {new_accountant_id}")
print()
print("Next steps:")
print("1. Refresh the dashboard in your browser")
print("2. Ask the agent: 'List my clients'")
print("3. You should now see all 5 clients")
