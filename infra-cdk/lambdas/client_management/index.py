# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Client Management Lambda

Handles client CRUD operations:
- Create new client
- Update client information
- Delete client (soft delete)
- Get client details
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

CLIENTS_TABLE = os.environ['CLIENTS_TABLE']


def create_client(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new client in DynamoDB.
    
    Args:
        client_data: Client information
    
    Returns:
        Created client with generated ID
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    # Generate client ID with format: LastName_UUID
    client_name = client_data['client_name']
    name_parts = client_name.strip().split()
    last_name = name_parts[-1] if name_parts else 'Client'
    # Remove special characters from last name
    last_name = ''.join(c for c in last_name if c.isalnum())
    
    # Generate short UUID (first 8 characters)
    short_uuid = str(uuid.uuid4())[:8]
    client_id = f"{last_name}_{short_uuid}"
    
    # Prepare client record
    client_record = {
        'client_id': client_id,
        'client_name': client_data['client_name'],
        'email': client_data['email'],
        'phone': client_data.get('phone', ''),
        'sms_enabled': client_data.get('sms_enabled', False),
        'client_type': client_data.get('client_type', 'individual'),
        'notes': client_data.get('notes', ''),
        'accountant_id': client_data['accountant_id'],  # From JWT
        'accountant_email': client_data.get('accountant_email', ''),
        'accountant_name': client_data.get('accountant_name', ''),
        'accountant_firm': client_data.get('accountant_firm', ''),
        'accountant_phone': client_data.get('accountant_phone', ''),
        'tax_year': 2026,  # Updated to 2026
        'status': 'incomplete',
        'created_at': datetime.utcnow().isoformat(),
        'last_updated': datetime.utcnow().isoformat(),
    }
    
    try:
        table.put_item(Item=client_record)
        logger.info(f"Created client: {client_record['client_name']} ({client_id})")
        return client_record
    except ClientError as e:
        logger.error(f"Error creating client: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for client management operations.
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Client management request: {json.dumps(event)}")
        
        http_method = event.get('httpMethod')
        body = json.loads(event.get('body', '{}'))
        
        # Extract accountant_id from JWT token
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        accountant_id = claims.get('sub')
        accountant_email = claims.get('email', '')
        
        if not accountant_id:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Unable to determine accountant ID from authentication'
                })
            }
        
        logger.info(f"Accountant ID from JWT: {accountant_id}")
        
        if http_method == 'POST':
            # Create new client
            required_fields = ['client_name', 'email']
            missing = [f for f in required_fields if not body.get(f)]
            
            if missing:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                    },
                    'body': json.dumps({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing)}'
                    })
                }
            
            # Add accountant_id from JWT to client data
            body['accountant_id'] = accountant_id
            body['accountant_email'] = accountant_email
            
            client = create_client(body)
            
            return {
                'statusCode': 201,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'success': True,
                    'client': client,
                    'message': f'Client "{client["client_name"]}" created successfully'
                })
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Method not allowed'
                })
            }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
        }
