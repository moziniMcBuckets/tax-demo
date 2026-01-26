# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Document Processor Lambda - Processes S3 upload events.

Triggered automatically when clients upload documents to S3.
Updates DynamoDB to mark documents as received and optionally
notifies the accountant when all documents are complete.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
SES_FROM_EMAIL = os.environ.get('SES_FROM_EMAIL', 'noreply@example.com')


def extract_metadata_from_s3(bucket: str, key: str) -> Dict[str, str]:
    """
    Extract metadata from S3 object.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        Dictionary of metadata
    """
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        return response.get('Metadata', {})
    except ClientError as e:
        logger.error(f"Error getting S3 metadata: {e}")
        return {}


def update_document_status(
    client_id: str,
    document_type: str,
    s3_path: str
) -> None:
    """
    Update document status in DynamoDB.
    
    Args:
        client_id: Client identifier
        document_type: Type of document
        s3_path: S3 path to document
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    try:
        table.update_item(
            Key={
                'client_id': client_id,
                'document_type': document_type
            },
            UpdateExpression='SET received = :r, received_date = :rd, file_path = :fp, last_updated = :lu',
            ExpressionAttributeValues={
                ':r': True,
                ':rd': datetime.utcnow().isoformat(),
                ':fp': s3_path,
                ':lu': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Updated document status: {client_id}/{document_type}")
        
    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e}")
        raise


def calculate_completion_percentage(client_id: str) -> int:
    """
    Calculate completion percentage for client.
    
    Args:
        client_id: Client identifier
    
    Returns:
        Completion percentage (0-100)
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='client_id = :cid',
            ExpressionAttributeValues={':cid': client_id}
        )
        
        documents = response.get('Items', [])
        required_docs = [d for d in documents if d.get('required', False)]
        received_docs = [d for d in required_docs if d.get('received', False)]
        
        if not required_docs:
            return 100
        
        return int((len(received_docs) / len(required_docs)) * 100)
        
    except ClientError as e:
        logger.error(f"Error calculating completion: {e}")
        return 0


def get_client_info(client_id: str) -> Dict[str, Any]:
    """Get client information."""
    table = dynamodb.Table(CLIENTS_TABLE)
    
    try:
        response = table.get_item(Key={'client_id': client_id})
        return response.get('Item', {})
    except ClientError as e:
        logger.error(f"Error getting client info: {e}")
        return {}


def send_completion_notification(client_id: str, client_info: Dict[str, Any]) -> None:
    """
    Send notification to accountant when client completes all documents.
    
    Args:
        client_id: Client identifier
        client_info: Client information dictionary
    """
    accountant_email = client_info.get('accountant_email')
    if not accountant_email:
        logger.info("No accountant email configured, skipping notification")
        return
    
    client_name = client_info.get('client_name', 'Unknown Client')
    
    subject = f"Good News: {client_name} has submitted all documents"
    body = f"""Great news!

Client {client_name} has successfully uploaded all required documents for their 2024 tax return.

You can now proceed with preparing their return.

This is an automated notification from the Tax Document Collection System.
"""
    
    try:
        ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [accountant_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}
            }
        )
        logger.info(f"Completion notification sent for client {client_id}")
    except ClientError as e:
        logger.error(f"Error sending completion notification: {e}")


def process_s3_upload(bucket: str, key: str) -> None:
    """
    Process S3 upload event.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    """
    logger.info(f"Processing upload: {bucket}/{key}")
    
    # Get object metadata (contains client_id, document_type, etc.)
    metadata = extract_metadata_from_s3(bucket, key)
    
    # Extract client_id from metadata (not from key path)
    client_id = metadata.get('client-id')
    document_type = metadata.get('document-type', 'Unknown')
    tax_year = metadata.get('tax-year', str(datetime.now().year))
    
    if not client_id:
        logger.error(f"No client-id in metadata for {key}, attempting to parse from key")
        # Fallback: try to parse from key if metadata missing
        parts = key.split('/')
        if len(parts) >= 2:
            # New format: lastName_FirstName_TaxYear/filename
            # We can't reliably extract client_id from this, so log error
            logger.error(f"Cannot determine client_id from key: {key}")
            return
        else:
            logger.error(f"Invalid S3 key format: {key}")
            return
    
    logger.info(f"Document type: {document_type}, Client: {client_id}, Tax Year: {tax_year}")
    
    # Update document status
    s3_path = f"s3://{bucket}/{key}"
    update_document_status(client_id, document_type, s3_path)
    
    # Check if client is now complete
    completion_pct = calculate_completion_percentage(client_id)
    logger.info(f"Client {client_id} completion: {completion_pct}%")
    
    if completion_pct == 100:
        # Send completion notification
        client_info = get_client_info(client_id)
        send_completion_notification(client_id, client_info)
        
        # Update client status
        clients_table = dynamodb.Table(CLIENTS_TABLE)
        try:
            clients_table.update_item(
                Key={'client_id': client_id},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'complete'}
            )
        except ClientError as e:
            logger.error(f"Error updating client status: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for S3 upload events.
    
    Args:
        event: S3 event notification
        context: Lambda context
    
    Returns:
        Success/error response
    """
    try:
        logger.info(f"Received S3 event: {json.dumps(event)}")
        
        # Process each S3 record
        for record in event.get('Records', []):
            event_name = record.get('eventName', '')
            
            # Only process object creation events
            if not event_name.startswith('ObjectCreated'):
                logger.info(f"Skipping non-creation event: {event_name}")
                continue
            
            # Extract S3 information
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Process the upload
            process_s3_upload(bucket, key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Upload processed successfully'})
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
