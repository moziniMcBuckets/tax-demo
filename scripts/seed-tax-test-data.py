#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Seed test data for Tax Document Agent.

Creates sample clients, document requirements, and follow-up history
for testing the tax document collection system.

Usage:
    python scripts/seed-tax-test-data.py
"""

import sys
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Add scripts directory to path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, print_msg, print_section


def get_table_names(stack_name: str) -> dict:
    """Get DynamoDB table names for the stack."""
    return {
        'clients': f'{stack_name}-clients',
        'documents': f'{stack_name}-documents',
        'followups': f'{stack_name}-followups',
        'settings': f'{stack_name}-settings',
    }


def create_sample_clients(dynamodb, table_name: str, accountant_id: str) -> list:
    """
    Create sample clients for testing.
    
    Args:
        dynamodb: DynamoDB resource
        table_name: Name of clients table
        accountant_id: Accountant identifier
    
    Returns:
        List of created client IDs
    """
    table = dynamodb.Table(table_name)
    
    clients = [
        {
            'client_id': str(uuid.uuid4()),
            'tax_year': 2024,
            'client_name': 'John Smith',
            'email': 'john.smith@example.com',
            'phone': '+1-555-0101',
            'accountant_id': accountant_id,
            'accountant_name': 'Sarah Johnson',
            'accountant_firm': 'Johnson Tax Services',
            'accountant_phone': '+1-555-0100',
            'status': 'incomplete',
            'created_at': datetime.utcnow().isoformat(),
        },
        {
            'client_id': str(uuid.uuid4()),
            'tax_year': 2024,
            'client_name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'phone': '+1-555-0102',
            'accountant_id': accountant_id,
            'accountant_name': 'Sarah Johnson',
            'accountant_firm': 'Johnson Tax Services',
            'accountant_phone': '+1-555-0100',
            'status': 'at_risk',
            'created_at': datetime.utcnow().isoformat(),
        },
        {
            'client_id': str(uuid.uuid4()),
            'tax_year': 2024,
            'client_name': 'Bob Wilson',
            'email': 'bob.wilson@example.com',
            'phone': '+1-555-0103',
            'accountant_id': accountant_id,
            'accountant_name': 'Sarah Johnson',
            'accountant_firm': 'Johnson Tax Services',
            'accountant_phone': '+1-555-0100',
            'status': 'complete',
            'created_at': datetime.utcnow().isoformat(),
        },
        {
            'client_id': str(uuid.uuid4()),
            'tax_year': 2024,
            'client_name': 'Alice Brown',
            'email': 'alice.brown@example.com',
            'phone': '+1-555-0104',
            'accountant_id': accountant_id,
            'accountant_name': 'Sarah Johnson',
            'accountant_firm': 'Johnson Tax Services',
            'accountant_phone': '+1-555-0100',
            'status': 'escalated',
            'created_at': datetime.utcnow().isoformat(),
        },
        {
            'client_id': str(uuid.uuid4()),
            'tax_year': 2024,
            'client_name': 'Charlie Davis',
            'email': 'charlie.davis@example.com',
            'phone': '+1-555-0105',
            'accountant_id': accountant_id,
            'accountant_name': 'Sarah Johnson',
            'accountant_firm': 'Johnson Tax Services',
            'accountant_phone': '+1-555-0100',
            'status': 'incomplete',
            'created_at': datetime.utcnow().isoformat(),
        },
    ]
    
    client_ids = []
    for client in clients:
        try:
            table.put_item(Item=client)
            client_ids.append(client['client_id'])
            print(f"  ✓ Created client: {client['client_name']} ({client['status']})")
        except ClientError as e:
            print(f"  ✗ Error creating client {client['client_name']}: {e}")
    
    return client_ids


def create_document_requirements(dynamodb, table_name: str, client_ids: list) -> None:
    """Create document requirements for sample clients."""
    table = dynamodb.Table(table_name)
    
    # Standard requirements for individual clients
    standard_docs = [
        ('W-2', 'All Employers', True),
        ('1099-INT', 'All Banks', False),
        ('1099-DIV', 'All Investment Accounts', False),
        ('Prior Year Tax Return', 'IRS', True),
    ]
    
    for client_id in client_ids:
        for doc_type, source, required in standard_docs:
            # Randomly mark some as received for variety
            received = (hash(client_id + doc_type) % 3 == 0)
            
            try:
                table.put_item(Item={
                    'client_id': client_id,
                    'document_type': doc_type,
                    'tax_year': 2024,
                    'source': source,
                    'required': required,
                    'received': received,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_checked': datetime.utcnow().isoformat(),
                })
            except ClientError as e:
                print(f"  ✗ Error creating requirement: {e}")


def create_followup_history(dynamodb, table_name: str, client_ids: list, accountant_id: str) -> None:
    """Create sample follow-up history."""
    table = dynamodb.Table(table_name)
    
    # Create follow-ups for first 3 clients
    for i, client_id in enumerate(client_ids[:3]):
        followup_count = i + 1  # 1, 2, 3 reminders
        
        for j in range(followup_count):
            days_ago = (followup_count - j) * 7
            sent_date = datetime.utcnow() - timedelta(days=days_ago)
            
            try:
                table.put_item(Item={
                    'client_id': client_id,
                    'followup_id': f'fu_{int(sent_date.timestamp())}',
                    'followup_number': j + 1,
                    'sent_date': sent_date.isoformat(),
                    'email_subject': f'Reminder #{j + 1}: Documents needed',
                    'email_body': 'Sample email body',
                    'documents_requested': ['W-2', '1099-INT'],
                    'response_received': False,
                    'next_followup_date': (sent_date + timedelta(days=7)).isoformat(),
                    'escalation_triggered': False,
                    'accountant_id': accountant_id,
                })
            except ClientError as e:
                print(f"  ✗ Error creating follow-up: {e}")


def create_accountant_settings(dynamodb, table_name: str, accountant_id: str) -> None:
    """Create accountant settings."""
    table = dynamodb.Table(table_name)
    
    settings = [
        {
            'accountant_id': accountant_id,
            'settings_type': 'preferences',
            'followup_schedule': [3, 7, 14],
            'escalation_threshold': 3,
            'escalation_days': 2,
        },
        {
            'accountant_id': accountant_id,
            'settings_type': 'contact_info',
            'email': 'accountant@example.com',
            'phone': '+1-555-0100',
            'name': 'Sarah Johnson',
            'firm': 'Johnson Tax Services',
        },
    ]
    
    for setting in settings:
        try:
            table.put_item(Item=setting)
            print(f"  ✓ Created setting: {setting['settings_type']}")
        except ClientError as e:
            print(f"  ✗ Error creating setting: {e}")


def main():
    """Main entry point."""
    print_section("Tax Document Agent - Seed Test Data")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Get table names
    tables = get_table_names(stack_name)
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb')
    
    # Generate accountant ID
    accountant_id = 'acc_test_001'
    
    # Create sample data
    print_section("Creating Sample Clients")
    client_ids = create_sample_clients(dynamodb, tables['clients'], accountant_id)
    print(f"\nCreated {len(client_ids)} clients")
    
    print_section("Creating Document Requirements")
    create_document_requirements(dynamodb, tables['documents'], client_ids)
    print_msg("Document requirements created")
    
    print_section("Creating Follow-up History")
    create_followup_history(dynamodb, tables['followups'], client_ids, accountant_id)
    print_msg("Follow-up history created")
    
    print_section("Creating Accountant Settings")
    create_accountant_settings(dynamodb, tables['settings'], accountant_id)
    
    print_section("Test Data Summary")
    print(f"Accountant ID: {accountant_id}")
    print(f"Clients created: {len(client_ids)}")
    print(f"\nClient IDs:")
    for i, client_id in enumerate(client_ids, 1):
        print(f"  {i}. {client_id}")
    
    print_msg("\nTest data seeded successfully!", "success")
    print("\nNext steps:")
    print("  1. Run: python scripts/test-tax-gateway.py")
    print("  2. Run: python scripts/test-tax-agent.py")


if __name__ == "__main__":
    main()
