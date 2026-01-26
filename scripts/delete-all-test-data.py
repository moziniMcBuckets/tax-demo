#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Delete All Test Data

Removes all data from DynamoDB tables and S3 bucket.
Use this to start fresh with a clean slate.

Usage:
    python3 scripts/delete-all-test-data.py
"""

import sys
from pathlib import Path
import boto3

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, print_msg, print_section

def main():
    """Main entry point."""
    print_section("Delete All Test Data")
    
    confirm = input("⚠️  This will DELETE ALL data. Are you sure? (type 'yes' to confirm): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    # Initialize clients
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    
    bucket_name = f"{stack_name}-client-docs-{account_id}"
    
    print(f"\nStack: {stack_name}")
    print(f"Bucket: {bucket_name}\n")
    
    # Delete from DynamoDB tables
    tables = ['clients', 'documents', 'followups', 'settings', 'feedback']
    
    for table_name in tables:
        full_table_name = f"{stack_name}-{table_name}"
        print(f"\nDeleting from {full_table_name}...")
        
        try:
            table = dynamodb.Table(full_table_name)
            
            # Scan and delete all items
            response = table.scan()
            items = response.get('Items', [])
            
            if not items:
                print(f"  ℹ Table is already empty")
                continue
            
            # Get table keys
            key_schema = table.key_schema
            keys = [k['AttributeName'] for k in key_schema]
            
            # Delete each item
            for item in items:
                key_dict = {k: item[k] for k in keys if k in item}
                table.delete_item(Key=key_dict)
            
            print(f"  ✓ Deleted {len(items)} items")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Delete from S3
    print(f"\nDeleting from S3 bucket {bucket_name}...")
    
    try:
        # List all objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        delete_count = 0
        for page in pages:
            if 'Contents' not in page:
                continue
            
            # Delete in batches of 1000
            objects = [{'Key': obj['Key']} for obj in page['Contents']]
            if objects:
                s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )
                delete_count += len(objects)
        
        if delete_count == 0:
            print(f"  ℹ Bucket is already empty")
        else:
            print(f"  ✓ Deleted {delete_count} files")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print_section("Summary")
    print_msg("All test data deleted successfully!", "success")
    print("\nYou now have a clean slate. Use the 'New Client' tab to add clients.")

if __name__ == "__main__":
    main()
