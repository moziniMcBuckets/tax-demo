# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Batch Operations Lambda

Handles bulk operations for multiple clients:
- Send reminders to multiple clients
- Send upload links to multiple clients
- Download all documents as ZIP

This Lambda calls the appropriate Gateway tools for each client and
aggregates the results.
"""

import json
import logging
import os
import io
import time
import zipfile
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
ses = boto3.client('ses')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
FOLLOWUPS_TABLE = os.environ['FOLLOWUPS_TABLE']
CLIENT_BUCKET = os.environ['CLIENT_BUCKET']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']
USAGE_TABLE = os.environ.get('USAGE_TABLE', '')


def track_usage(accountant_id: str, operation: str, resource_type: str, quantity: float = 1.0):
    """Track usage for billing."""
    if not USAGE_TABLE:
        return
    
    try:
        from datetime import datetime
        from decimal import Decimal
        
        usage_table = dynamodb.Table(USAGE_TABLE)
        timestamp = datetime.utcnow().isoformat()
        month = timestamp[:7]
        
        # Pricing
        pricing = {
            'email_sent': 0.0001,
            'agent_invocation': 0.003,
            'gateway_call': 0.0001,
        }
        
        unit_cost = pricing.get(resource_type, 0.0)
        estimated_cost = unit_cost * quantity
        
        usage_table.put_item(Item={
            'accountant_id': accountant_id,
            'timestamp': timestamp,
            'month': month,
            'operation': operation,
            'resource_type': resource_type,
            'quantity': Decimal(str(quantity)),  # Convert to Decimal
            'unit_cost': Decimal(str(unit_cost)),
            'estimated_cost': Decimal(str(estimated_cost))
        })
        
        logger.info(f"Tracked usage: {operation}, cost: ${estimated_cost:.6f}")
    except Exception as e:
        logger.error(f"Error tracking usage: {e}")


def get_client_info(client_id: str) -> Dict[str, Any]:
    """
    Get client information from DynamoDB.
    
    Args:
        client_id: Client identifier
    
    Returns:
        Client information dictionary
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    try:
        response = table.get_item(Key={'client_id': client_id})
        return response.get('Item', {})
    except ClientError as e:
        logger.error(f"Error getting client info: {e}")
        return {}


def send_reminder_to_client(client_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send reminder to a single client by calling SES directly.
    
    Args:
        client_id: Client identifier
        options: Operation options (custom_message, etc.)
    
    Returns:
        Result dictionary with success status
    """
    client_info = get_client_info(client_id)
    client_name = client_info.get('client_name', 'Unknown')
    client_email = client_info.get('email')
    
    if not client_email:
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': False,
            'error': 'No email address on file'
        }
    
    try:
        # Get missing documents
        docs_table = dynamodb.Table(DOCUMENTS_TABLE)
        doc_response = docs_table.query(
            KeyConditionExpression='client_id = :cid',
            ExpressionAttributeValues={':cid': client_id}
        )
        
        missing_docs = [
            d['document_type'] 
            for d in doc_response.get('Items', [])
            if d.get('required', False) and not d.get('received', False)
        ]
        
        if not missing_docs:
            return {
                'client_id': client_id,
                'client_name': client_name,
                'success': False,
                'error': 'All documents already received'
            }
        
        # Create email
        subject = f"Reminder: Documents needed for your 2026 tax return"
        body = f"""Dear {client_name},

This is a friendly reminder that we still need the following documents to complete your 2026 tax return:

{chr(10).join(f'{i}. {doc}' for i, doc in enumerate(missing_docs, 1))}

Please upload these documents at your earliest convenience.

Thank you,
Your Accountant
"""
        
        # Send via SES
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [client_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        
        logger.info(f"Sent reminder to {client_name} ({client_email})")
        
        # Track usage
        track_usage(
            accountant_id=client_info.get('accountant_id', 'unknown'),
            operation='send_reminder',
            resource_type='email_sent',
            quantity=1
        )
        
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': True,
            'message': f'Reminder sent to {client_email}'
        }
    except Exception as e:
        logger.error(f"Error sending reminder to {client_id}: {e}")
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': False,
            'error': str(e)
        }


def send_upload_link_to_client(client_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send upload link to a single client by generating token and calling SES.
    
    Args:
        client_id: Client identifier
        options: Operation options (days_valid, custom_message, reminder_preferences, etc.)
    
    Returns:
        Result dictionary with success status
    """
    import secrets
    from datetime import datetime, timedelta
    
    client_info = get_client_info(client_id)
    client_name = client_info.get('client_name', 'Unknown')
    client_email = client_info.get('email')
    
    if not client_email:
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': False,
            'error': 'No email address on file'
        }
    
    try:
        days_valid = options.get('days_valid', 30)
        custom_message = options.get('custom_message')
        reminder_preferences = options.get('reminder_preferences')
        
        # Generate upload token
        upload_token = secrets.token_urlsafe(32)
        token_expires = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
        
        # Update client record with token and optional reminder preferences
        clients_table = dynamodb.Table(CLIENTS_TABLE)
        
        update_expression = 'SET upload_token = :token, token_expires = :expires'
        expression_values = {
            ':token': upload_token,
            ':expires': token_expires
        }
        
        # Add reminder preferences if provided
        if reminder_preferences:
            update_expression += ', reminder_preferences = :prefs'
            expression_values[':prefs'] = reminder_preferences
        
        clients_table.update_item(
            Key={'client_id': client_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        # Generate upload URL
        frontend_url = os.environ.get('FRONTEND_URL', 'https://main.d3tseyzyms135a.amplifyapp.com')
        upload_url = f"{frontend_url}/upload/?client={client_id}&token={upload_token}"
        
        # Create email
        subject = f"Secure Link to Upload Your 2026 Tax Documents"
        body = f"""Dear {client_name},

Please upload your tax documents using this secure link:

{upload_url}

This link is valid for {days_valid} days and is unique to you. No login is required.

"""
        
        # Add custom message if provided
        if custom_message:
            body += f"{custom_message}\n\n"
        
        body += """Thank you,
Your Accountant
"""
        
        # Send via SES
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [client_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        
        logger.info(f"Sent upload link to {client_name} ({client_email})")
        
        # Track usage
        track_usage(
            accountant_id=client_info.get('accountant_id', 'unknown'),
            operation='send_upload_link',
            resource_type='email_sent',
            quantity=1
        )
        
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': True,
            'message': f'Upload link sent to {client_email}'
        }
    except Exception as e:
        logger.error(f"Error sending upload link to {client_id}: {e}")
        return {
            'client_id': client_id,
            'client_name': client_name,
            'success': False,
            'error': str(e)
        }


def download_all_documents(client_ids: List[str]) -> Dict[str, Any]:
    """
    Create ZIP archive of all documents for selected clients.
    
    Args:
        client_ids: List of client identifiers
    
    Returns:
        Result with S3 URL to download ZIP
    """
    try:
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            total_files = 0
            
            for client_id in client_ids:
                client_info = get_client_info(client_id)
                client_name = client_info.get('client_name', 'Unknown')
                
                # Create folder name
                name_parts = client_name.strip().split()
                if len(name_parts) >= 2:
                    first_name = '_'.join(name_parts[:-1])
                    last_name = name_parts[-1]
                    folder_name = f"{last_name}_{first_name}_2026"
                else:
                    folder_name = f"{client_name.replace(' ', '_')}_2026"
                
                folder_name = ''.join(c for c in folder_name if c.isalnum() or c in '_-')
                
                # List files in S3
                try:
                    response = s3.list_objects_v2(
                        Bucket=CLIENT_BUCKET,
                        Prefix=f"{folder_name}/"
                    )
                    
                    if 'Contents' in response:
                        for obj in response['Contents']:
                            key = obj['Key']
                            if key.endswith('/'):
                                continue
                            
                            # Download file from S3
                            file_obj = s3.get_object(Bucket=CLIENT_BUCKET, Key=key)
                            file_content = file_obj['Body'].read()
                            
                            # Add to ZIP with client folder structure
                            zip_file.writestr(key, file_content)
                            total_files += 1
                            
                except ClientError as e:
                    logger.warning(f"No documents found for {client_name}: {e}")
                    continue
        
        if total_files == 0:
            return {
                'success': False,
                'error': 'No documents found for selected clients'
            }
        
        # Upload ZIP to S3
        zip_buffer.seek(0)
        zip_key = f"bulk-downloads/download-{int(time.time())}.zip"
        
        s3.put_object(
            Bucket=CLIENT_BUCKET,
            Key=zip_key,
            Body=zip_buffer.getvalue(),
            ContentType='application/zip'
        )
        
        # Generate presigned URL (valid for 1 hour)
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': CLIENT_BUCKET, 'Key': zip_key},
            ExpiresIn=3600
        )
        
        return {
            'success': True,
            'total_files': total_files,
            'download_url': download_url,
            'expires_in': 3600
        }
        
    except Exception as e:
        logger.error(f"Error creating ZIP: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for batch operations.
    
    Args:
        event: API Gateway event with operation and client_ids
        context: Lambda context
    
    Returns:
        API Gateway response with operation results
    """
    try:
        logger.info(f"Batch operation request: {json.dumps(event)}")
        
        # Extract accountant_id from JWT token
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        accountant_id = claims.get('sub')
        
        if not accountant_id:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Unable to determine accountant ID from authentication'
                })
            }
        
        logger.info(f"Accountant ID from JWT: {accountant_id}")
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        operation = body.get('operation')
        client_ids = body.get('client_ids', [])
        options = body.get('options', {})
        
        if not operation or not client_ids:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Missing required parameters: operation, client_ids'
                })
            }
        
        logger.info(f"Operation: {operation}, Clients: {len(client_ids)}")
        
        # Process based on operation type
        if operation == 'send_reminders':
            # Process in parallel (max 10 concurrent)
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(send_reminder_to_client, client_id, options): client_id
                    for client_id in client_ids
                }
                
                results = []
                for future in as_completed(futures):
                    results.append(future.result())
            
            succeeded = len([r for r in results if r['success']])
            failed = len([r for r in results if not r['success']])
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'success': True,
                    'operation': 'send_reminders',
                    'total': len(client_ids),
                    'succeeded': succeeded,
                    'failed': failed,
                    'results': results
                })
            }
        
        elif operation == 'send_upload_links':
            # Process in parallel
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(send_upload_link_to_client, client_id, options): client_id
                    for client_id in client_ids
                }
                
                results = []
                for future in as_completed(futures):
                    results.append(future.result())
            
            succeeded = len([r for r in results if r['success']])
            failed = len([r for r in results if not r['success']])
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'success': True,
                    'operation': 'send_upload_links',
                    'total': len(client_ids),
                    'succeeded': succeeded,
                    'failed': failed,
                    'results': results
                })
            }
        
        elif operation == 'download_all':
            result = download_all_documents(client_ids)
            
            return {
                'statusCode': 200 if result['success'] else 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'success': result['success'],
                    'operation': 'download_all',
                    'total_files': result.get('total_files', 0),
                    'download_url': result.get('download_url'),
                    'expires_in': result.get('expires_in'),
                    'error': result.get('error')
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': f'Unknown operation: {operation}'
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
