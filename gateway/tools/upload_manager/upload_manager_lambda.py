# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Upload Manager Lambda - Generate presigned URLs for client document uploads.

This Lambda generates secure, time-limited S3 presigned URLs that allow clients
to upload documents directly to S3 without going through API Gateway or Lambda.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

CLIENT_BUCKET = os.environ['CLIENT_BUCKET']
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']


def validate_client(client_id: str, upload_token: str) -> bool:
    """
    Validate client has permission to upload.
    
    Args:
        client_id: Client identifier
        upload_token: Secure token sent to client via email
    
    Returns:
        True if valid, False otherwise
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    try:
        response = table.get_item(Key={'client_id': client_id})
        
        if 'Item' not in response:
            logger.warning(f"Client not found: {client_id}")
            return False
        
        client = response['Item']
        
        # Check if upload token matches
        stored_token = client.get('upload_token')
        if not stored_token or stored_token != upload_token:
            logger.warning(f"Invalid upload token for client: {client_id}")
            return False
        
        # Check if token is expired
        token_expires = client.get('token_expires')
        if token_expires:
            expires_dt = datetime.fromisoformat(token_expires)
            if datetime.utcnow() > expires_dt:
                logger.warning(f"Upload token expired for client: {client_id}")
                return False
        
        return True
        
    except ClientError as e:
        logger.error(f"Error validating client: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for S3 storage.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Replace spaces with underscores
    safe_name = filename.replace(' ', '_')
    
    # Remove potentially dangerous characters
    safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '._-')
    
    # Limit length
    if len(safe_name) > 100:
        # Keep extension
        parts = safe_name.rsplit('.', 1)
        if len(parts) == 2:
            safe_name = parts[0][:95] + '.' + parts[1]
        else:
            safe_name = safe_name[:100]
    
    return safe_name


def generate_presigned_url(
    client_id: str,
    filename: str,
    tax_year: int,
    document_type: str
) -> Dict[str, Any]:
    """
    Generate presigned URL for S3 upload.
    
    Args:
        client_id: Client identifier
        filename: Name of file to upload
        tax_year: Tax year
        document_type: Type of document (W-2, 1099-INT, etc.)
    
    Returns:
        Dictionary with presigned URL and metadata
    """
    # Sanitize filename
    safe_filename = sanitize_filename(filename)
    
    # S3 key with client folder structure
    s3_key = f"{client_id}/{tax_year}/{safe_filename}"
    
    try:
        # Generate presigned URL (valid for 15 minutes)
        url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': CLIENT_BUCKET,
                'Key': s3_key,
                'ContentType': 'application/pdf',
                'Metadata': {
                    'document-type': document_type,
                    'tax-year': str(tax_year),
                    'upload-date': datetime.utcnow().isoformat(),
                    'client-id': client_id,
                }
            },
            ExpiresIn=900  # 15 minutes
        )
        
        logger.info(f"Generated presigned URL for {client_id}/{safe_filename}")
        
        return {
            'upload_url': url,
            's3_key': s3_key,
            'expires_in': 900,
            'bucket': CLIENT_BUCKET,
        }
        
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating upload URLs.
    
    Args:
        event: API Gateway event with client_id, filename, document_type
        context: Lambda context
    
    Returns:
        API Gateway response with presigned URL
    """
    try:
        logger.info(f"Upload URL request: {json.dumps(event)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        client_id = body.get('client_id')
        upload_token = body.get('upload_token')
        filename = body.get('filename')
        tax_year = body.get('tax_year', datetime.now().year)
        document_type = body.get('document_type', 'Unknown')
        
        # Validate required parameters
        if not all([client_id, upload_token, filename]):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Missing required parameters: client_id, upload_token, filename'
                })
            }
        
        # Validate file type
        if not filename.lower().endswith('.pdf'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Only PDF files are allowed'
                })
            }
        
        # Validate client and token
        if not validate_client(client_id, upload_token):
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Invalid client ID or upload token'
                })
            }
        
        # Generate presigned URL
        result = generate_presigned_url(
            client_id=client_id,
            filename=filename,
            tax_year=tax_year,
            document_type=document_type
        )
        
        logger.info(f"Presigned URL generated successfully for client {client_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'success': True,
                'upload_url': result['upload_url'],
                'expires_in': result['expires_in'],
                's3_key': result['s3_key'],
                'instructions': 'Use PUT request to upload file to upload_url'
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
