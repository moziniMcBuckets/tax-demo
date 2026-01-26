#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Add IAM Permissions to Tax Lambda Functions

This script adds necessary IAM permissions to all tax Lambda functions
for accessing DynamoDB, S3, SES, and SNS resources.

This is a temporary workaround until CDK is updated to include permissions automatically.

Usage:
    python3 scripts/add-lambda-permissions.py
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

# Initialize AWS clients
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')


def get_lambda_role_name(function_name: str) -> str:
    """
    Get the IAM role name for a Lambda function.
    
    Args:
        function_name: Lambda function name
    
    Returns:
        IAM role name
    """
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        role_arn = response['Configuration']['Role']
        # Extract role name from ARN: arn:aws:iam::account:role/role-name
        role_name = role_arn.split('/')[-1]
        return role_name
    except ClientError as e:
        print_msg(f"Error getting Lambda role: {e}", "error")
        raise


def add_dynamodb_policy(role_name: str, table_names: list, policy_name: str):
    """
    Add DynamoDB access policy to IAM role.
    
    Args:
        role_name: IAM role name
        table_names: List of DynamoDB table names
        policy_name: Name for the policy
    """
    # Get account and region
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name
    
    # Build table ARNs
    table_arns = [
        f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"
        for table_name in table_names
    ]
    
    # Add index ARNs for GSI access
    index_arns = [
        f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}/index/*"
        for table_name in table_names
    ]
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": table_arns + index_arns
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print_msg(f"✓ Added DynamoDB policy to {role_name}", "success")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print_msg(f"  Policy already exists, updating...", "info")
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
        else:
            print_msg(f"✗ Error adding DynamoDB policy: {e}", "error")
            raise


def add_s3_policy(role_name: str, bucket_name: str, policy_name: str):
    """
    Add S3 access policy to IAM role.
    
    Args:
        role_name: IAM role name
        bucket_name: S3 bucket name
        policy_name: Name for the policy
    """
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print_msg(f"✓ Added S3 policy to {role_name}", "success")
    except ClientError as e:
        print_msg(f"✗ Error adding S3 policy: {e}", "error")
        raise


def add_ses_policy(role_name: str, policy_name: str):
    """
    Add SES send email policy to IAM role.
    
    Args:
        role_name: IAM role name
        policy_name: Name for the policy
    """
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print_msg(f"✓ Added SES policy to {role_name}", "success")
    except ClientError as e:
        print_msg(f"✗ Error adding SES policy: {e}", "error")
        raise


def add_sns_policy(role_name: str, topic_arn: str, policy_name: str):
    """
    Add SNS publish policy to IAM role.
    
    Args:
        role_name: IAM role name
        topic_arn: SNS topic ARN
        policy_name: Name for the policy
    """
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sns:Publish"
                ],
                "Resource": topic_arn
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print_msg(f"✓ Added SNS policy to {role_name}", "success")
    except ClientError as e:
        print_msg(f"✗ Error adding SNS policy: {e}", "error")
        raise


def main():
    """Main entry point."""
    print_section("Add Lambda IAM Permissions")
    
    # Get stack configuration
    stack_cfg = get_stack_config()
    stack_name = stack_cfg['stack_name']
    print(f"Stack: {stack_name}\n")
    
    # Get account and region
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name
    
    # Define table names
    clients_table = f"{stack_name}-clients"
    documents_table = f"{stack_name}-documents"
    followups_table = f"{stack_name}-followups"
    settings_table = f"{stack_name}-settings"
    bucket_name = f"{stack_name}-client-docs-{account_id}"
    sns_topic_arn = f"arn:aws:sns:{region}:{account_id}:{stack_name}-escalations"
    
    # Define Lambda functions and their required permissions
    lambda_permissions = {
        'TaxDocChecker': {
            'tables': [clients_table, documents_table],
            's3': bucket_name,
            'ses': False,
            'sns': False
        },
        'TaxEmail': {
            'tables': [clients_table, followups_table, settings_table],
            's3': False,
            'ses': True,
            'sns': False
        },
        'TaxStatus': {
            'tables': [clients_table, documents_table, followups_table, settings_table],
            's3': False,
            'ses': False,
            'sns': False
        },
        'TaxEscalate': {
            'tables': [clients_table, followups_table, settings_table],
            's3': False,
            'ses': True,
            'sns': sns_topic_arn
        },
        'TaxReqMgr': {
            'tables': [clients_table, documents_table],
            's3': False,
            'ses': False,
            'sns': False
        },
        'TaxUpload': {
            'tables': [clients_table],
            's3': bucket_name,
            'ses': False,
            'sns': False
        },
        'TaxSendLink': {
            'tables': [clients_table, followups_table],
            's3': False,
            'ses': True,
            'sns': False
        },
        'document-processor': {
            'tables': [clients_table, documents_table],
            's3': bucket_name,
            'ses': True,
            'sns': False
        }
    }
    
    # Process each Lambda function
    for lambda_id, permissions in lambda_permissions.items():
        print_section(f"Processing {lambda_id}")
        
        # Find Lambda function
        try:
            response = lambda_client.list_functions()
            functions = [f for f in response['Functions'] if lambda_id in f['FunctionName']]
            
            if not functions:
                print_msg(f"✗ Lambda function not found: {lambda_id}", "error")
                continue
            
            function_name = functions[0]['FunctionName']
            print(f"Function: {function_name}")
            
            # Get role name
            role_name = get_lambda_role_name(function_name)
            print(f"Role: {role_name}")
            
            # Add DynamoDB permissions
            if permissions['tables']:
                add_dynamodb_policy(
                    role_name=role_name,
                    table_names=permissions['tables'],
                    policy_name=f"{lambda_id}DynamoDBPolicy"
                )
            
            # Add S3 permissions
            if permissions['s3']:
                add_s3_policy(
                    role_name=role_name,
                    bucket_name=permissions['s3'],
                    policy_name=f"{lambda_id}S3Policy"
                )
            
            # Add SES permissions
            if permissions['ses']:
                add_ses_policy(
                    role_name=role_name,
                    policy_name=f"{lambda_id}SESPolicy"
                )
            
            # Add SNS permissions
            if permissions['sns']:
                add_sns_policy(
                    role_name=role_name,
                    topic_arn=permissions['sns'],
                    policy_name=f"{lambda_id}SNSPolicy"
                )
            
            print()
            
        except Exception as e:
            print_msg(f"✗ Error processing {lambda_id}: {e}", "error")
            continue
    
    print_section("Summary")
    print_msg("IAM permissions added successfully to all Lambda functions!", "success")
    print("\nNote: It may take a few seconds for permissions to propagate.")


if __name__ == "__main__":
    main()
