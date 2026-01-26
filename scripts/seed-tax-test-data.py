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


def create_sample_pdf(document_type: str, client_name: str) -> bytes:
    """
    Create a simple sample PDF for testing.
    
    Args:
        document_type: Type of document (W-2, 1099, etc.)
        client_name: Client name
    
    Returns:
        PDF content as bytes
    """
    # Simple PDF content (minimal valid PDF)
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Length 150
>>
stream
BT
/F1 24 Tf
50 700 Td
(SAMPLE {document_type}) Tj
0 -30 Td
/F1 12 Tf
(Client: {client_name}) Tj
0 -20 Td
(Tax Year: 2024) Tj
0 -20 Td
(This is a test document for demonstration purposes.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
517
%%EOF
"""
    return pdf_content.encode('latin-1')


def upload_sample_pdf(
    s3_client,
    bucket_name: str,
    client_id: str,
    client_name: str,
    document_type: str,
    tax_year: int
) -> None:
    """
    Upload a sample PDF to S3.
    
    Args:
        s3_client: S3 client
        bucket_name: S3 bucket name
        client_id: Client identifier
        client_name: Client full name
        document_type: Type of document
        tax_year: Tax year
    """
    # Create folder name: lastName_FirstName_TaxYear
    name_parts = client_name.strip().split()
    if len(name_parts) >= 2:
        first_name = '_'.join(name_parts[:-1])
        last_name = name_parts[-1]
        folder_name = f"{last_name}_{first_name}_{tax_year}"
    else:
        folder_name = f"{client_name.replace(' ', '_')}_{tax_year}"
    
    folder_name = ''.join(c for c in folder_name if c.isalnum() or c in '_-')
    
    # Create filename
    filename = f"{document_type.replace(' ', '-').replace('/', '-')}-Sample.pdf"
    s3_key = f"{folder_name}/{filename}"
    
    try:
        # Create sample PDF
        pdf_content = create_sample_pdf(document_type, client_name)
        
        # Upload to S3 with metadata
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=pdf_content,
            ContentType='application/pdf',
            Metadata={
                'document-type': document_type,
                'tax-year': str(tax_year),
                'upload-date': datetime.utcnow().isoformat(),
                'client-id': client_id,
                'sample-data': 'true'
            }
        )
        
        print(f"    ✓ Uploaded sample {document_type} for {client_name}")
        
    except ClientError as e:
        print(f"    ✗ Error uploading sample PDF: {e}")


def get_table_names(stack_name: str) -> dict:
    """Get DynamoDB table names for the stack."""
    return {
        'clients': f'{stack_name}-clients',
        'documents': f'{stack_name}-documents',
        'followups': f'{stack_name}-followups',
        'settings': f'{stack_name}-settings',
    }


def create_sample_clients(dynamodb, table_name: str, accountant_id: str) -> tuple:
    """
    Create sample clients for testing.
    
    Args:
        dynamodb: DynamoDB resource
        table_name: Name of clients table
        accountant_id: Accountant identifier
    
    Returns:
        Tuple of (client_ids list, clients_data list)
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
    
    return client_ids, clients


def create_document_requirements(dynamodb, s3_client, table_name: str, bucket_name: str, client_ids: list, clients_data: list) -> None:
    """
    Create document requirements for sample clients and upload sample PDFs.
    
    NOTE: This function is now minimal - it only creates requirements that accountants
    explicitly add. No predefined requirements are assumed.
    
    Args:
        dynamodb: DynamoDB resource
        s3_client: S3 client
        table_name: Documents table name
        bucket_name: S3 bucket name
        client_ids: List of client IDs
        clients_data: List of client data dictionaries
    """
    # No predefined requirements - accountants will add them via UI or agent
    print("  ℹ No predefined requirements - accountants will define per client")
    print("  ℹ Use the UI or agent to add requirements for each client")


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
    
    # Get table names and bucket name
    tables = get_table_names(stack_name)
    
    # Get account ID for bucket name
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    bucket_name = f"{stack_name}-client-docs-{account_id}"
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    s3_client = boto3.client('s3')
    
    # Generate accountant ID
    accountant_id = 'acc_test_001'
    
    # Create sample data
    print_section("Creating Sample Clients")
    clients_data = [
        {'client_name': 'John Smith'},
        {'client_name': 'Jane Doe'},
        {'client_name': 'Bob Wilson'},
        {'client_name': 'Alice Brown'},
        {'client_name': 'Charlie Davis'},
    ]
    client_ids, clients = create_sample_clients(dynamodb, tables['clients'], accountant_id)
    print(f"\nCreated {len(client_ids)} clients")
    
    print_section("Creating Document Requirements & Uploading Sample PDFs")
    create_document_requirements(dynamodb, s3_client, tables['documents'], bucket_name, client_ids, clients)
    print_msg("Document requirements created and sample PDFs uploaded")
    
    print_section("Creating Follow-up History")
    create_followup_history(dynamodb, tables['followups'], client_ids, accountant_id)
    print_msg("Follow-up history created")
    
    print_section("Creating Accountant Settings")
    create_accountant_settings(dynamodb, tables['settings'], accountant_id)
    
    print_section("Test Data Summary")
    print(f"Accountant ID: {accountant_id}")
    print(f"Clients created: {len(client_ids)}")
    print(f"S3 Bucket: {bucket_name}")
    print(f"\nClient IDs:")
    for i, client_id in enumerate(client_ids, 1):
        print(f"  {i}. {client_id}")
    
    print_msg("\nTest data seeded successfully!", "success")
    print("\nNext steps:")
    print("  1. Run: python scripts/test-tax-gateway.py")
    print("  2. Run: python scripts/test-tax-agent.py")
    print("  3. Check S3 bucket for sample PDFs")


if __name__ == "__main__":
    main()
