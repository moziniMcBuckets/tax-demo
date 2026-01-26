#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Configure S3 CORS for Client Documents Bucket

Adds CORS configuration to allow uploads from the frontend.

Usage:
    python3 scripts/configure-s3-cors.py
"""

import sys
import json
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from utils import get_stack_config, print_msg, print_section

s3 = boto3.client('s3')


def configure_bucket_cors(bucket_name: str, frontend_url: str):
    """
    Configure CORS for S3 bucket.
    
    Args:
        bucket_name: S3 bucket name
        frontend_url: Frontend URL to allow
    """
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'HEAD'],
                'AllowedOrigins': [
                    frontend_url,
                    'http://localhost:3000',
                    'https://*.amplifyapp.com'
                ],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ]
    }
    
    try:
        s3.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print_msg(f"✓ CORS configured for bucket: {bucket_name}", "success")
        print(f"\nAllowed origins:")
        for origin in cors_configuration['CORSRules'][0]['AllowedOrigins']:
            print(f"  - {origin}")
    except ClientError as e:
        print_msg(f"✗ Error configuring CORS: {e}", "error")
        raise


def main():
    """Main entry point."""
    print_section("Configure S3 CORS for Client Documents")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    # Construct bucket name
    bucket_name = f"{stack_name}-client-docs-{account_id}"
    
    # Get frontend URL from stack outputs
    frontend_url = stack_cfg.get('AmplifyUrl', 'https://main.*.amplifyapp.com')
    
    print(f"Stack: {stack_name}")
    print(f"Bucket: {bucket_name}")
    print(f"Frontend URL: {frontend_url}\n")
    
    # Configure CORS
    configure_bucket_cors(bucket_name, frontend_url)
    
    print_section("Summary")
    print_msg("S3 CORS configuration completed successfully!", "success")
    print("\nClients can now upload documents directly to S3 from the frontend.")


if __name__ == "__main__":
    main()
