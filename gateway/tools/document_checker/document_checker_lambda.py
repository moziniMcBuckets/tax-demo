# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Document Checker Lambda - Scans S3 client folders and identifies missing documents.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
CLIENT_BUCKET = os.environ['CLIENT_BUCKET']

# Document type patterns for classification
DOCUMENT_PATTERNS = {
    'W-2': ['w2', 'w-2', 'wage', 'tax statement'],
    '1099-INT': ['1099-int', '1099int', 'interest income'],
    '1099-DIV': ['1099-div', '1099div', 'dividend'],
    '1099-MISC': ['1099-misc', '1099misc', 'miscellaneous'],
    '1099-NEC': ['1099-nec', '1099nec', 'non-employee'],
    '1099-B': ['1099-b', '1099b', 'broker'],
    '1099-R': ['1099-r', '1099r', 'retirement'],
}


def classify_document(filename: str, metadata: Dict[str, str]) -> str:
    """
    Classify document type based on filename and S3 metadata.
    
    Args:
        filename: Name of the file
        metadata: S3 object metadata
    
    Returns:
        Document type string (e.g., 'W-2', '1099-INT', 'Unknown')
    """
    filename_lower = filename.lower()
    
    # Check metadata first (most reliable)
    if 'document-type' in metadata:
        return metadata['document-type']
    
    # Pattern matching on filename
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        if any(pattern in filename_lower for pattern in patterns):
            return doc_type
    
    return 'Unknown'


def scan_client_folder(client_id: str, tax_year: int) -> List[Dict[str, Any]]:
    """
    Scan S3 folder for client documents.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year to scan
    
    Returns:
        List of document dictionaries with metadata
    """
    prefix = f"{client_id}/{tax_year}/"
    documents = []
    
    try:
        # List objects in client folder
        response = s3.list_objects_v2(
            Bucket=CLIENT_BUCKET,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.info(f"No documents found for client {client_id}, year {tax_year}")
            return documents
        
        # Process each document
        for obj in response['Contents']:
            key = obj['Key']
            
            # Skip folder markers
            if key.endswith('/'):
                continue
            
            # Get object metadata (no data transfer cost!)
            head_response = s3.head_object(Bucket=CLIENT_BUCKET, Key=key)
            metadata = head_response.get('Metadata', {})
            
            filename = key.split('/')[-1]
            doc_type = classify_document(filename, metadata)
            
            documents.append({
                'filename': filename,
                'document_type': doc_type,
                'upload_date': obj['LastModified'].isoformat(),
                'size_bytes': obj['Size'],
                's3_key': key,
            })
        
        logger.info(f"Found {len(documents)} documents for client {client_id}")
        return documents
        
    except ClientError as e:
        logger.error(f"Error scanning S3 folder: {e}")
        raise


def get_required_documents(client_id: str, tax_year: int) -> List[Dict[str, Any]]:
    """
    Get list of required documents from DynamoDB.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year
    
    Returns:
        List of required document dictionaries
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='client_id = :cid',
            ExpressionAttributeValues={':cid': client_id}
        )
        
        required_docs = [
            item for item in response['Items']
            if item.get('required', False) and item.get('tax_year') == tax_year
        ]
        
        return required_docs
        
    except ClientError as e:
        logger.error(f"Error querying DynamoDB: {e}")
        raise


def update_document_status(
    client_id: str,
    tax_year: int,
    received_documents: List[Dict[str, Any]]
) -> None:
    """
    Update document receipt status in DynamoDB.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year
        received_documents: List of received documents
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    # Create a map of received document types
    received_types = {doc['document_type'] for doc in received_documents}
    
    try:
        # Get all required documents
        required_docs = get_required_documents(client_id, tax_year)
        
        # Update each document's status
        for doc in required_docs:
            doc_type = doc['document_type']
            received = doc_type in received_types
            
            table.update_item(
                Key={
                    'client_id': client_id,
                    'document_type': doc_type
                },
                UpdateExpression='SET received = :r, last_checked = :lc',
                ExpressionAttributeValues={
                    ':r': received,
                    ':lc': datetime.utcnow().isoformat()
                }
            )
        
        logger.info(f"Updated document status for client {client_id}")
        
    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e}")
        raise


def calculate_completion_percentage(
    required_docs: List[Dict[str, Any]],
    received_docs: List[Dict[str, Any]]
) -> int:
    """
    Calculate completion percentage.
    
    Args:
        required_docs: List of required documents
        received_docs: List of received documents
    
    Returns:
        Completion percentage (0-100)
    """
    if not required_docs:
        return 100
    
    received_types = {doc['document_type'] for doc in received_docs}
    required_types = {doc['document_type'] for doc in required_docs}
    
    matched = len(received_types & required_types)
    total = len(required_types)
    
    return int((matched / total) * 100)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document checking.
    
    Args:
        event: Lambda event containing client_id and tax_year
        context: Lambda context object
    
    Returns:
        Dictionary with document status information
    """
    try:
        # Extract tool name from context
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Tool invoked: {tool_name}")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Extract parameters
        client_id = event.get('client_id')
        tax_year = event.get('tax_year')
        
        if not client_id or not tax_year:
            raise ValueError("Missing required parameters: client_id, tax_year")
        
        # Scan client folder
        received_documents = scan_client_folder(client_id, tax_year)
        
        # Get required documents
        required_documents = get_required_documents(client_id, tax_year)
        
        # Update status in DynamoDB
        update_document_status(client_id, tax_year, received_documents)
        
        # Calculate completion
        completion_pct = calculate_completion_percentage(
            required_documents,
            received_documents
        )
        
        # Identify missing documents
        received_types = {doc['document_type'] for doc in received_documents}
        missing_docs = [
            {
                'type': doc['document_type'],
                'source': doc.get('source', 'Unknown'),
                'required': doc.get('required', False)
            }
            for doc in required_documents
            if doc['document_type'] not in received_types
        ]
        
        # Determine status
        if completion_pct == 100:
            status = 'complete'
        elif completion_pct >= 50:
            status = 'incomplete'
        else:
            status = 'at_risk'
        
        # Build response
        response = {
            'client_id': client_id,
            'tax_year': tax_year,
            'status': status,
            'completion_percentage': completion_pct,
            'required_documents': [
                {
                    'type': doc['document_type'],
                    'source': doc.get('source', 'Unknown'),
                    'received': doc['document_type'] in received_types,
                    'last_checked': datetime.utcnow().isoformat()
                }
                for doc in required_documents
            ],
            'received_documents': received_documents,
            'missing_documents': missing_docs,
            'last_checked': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Document check complete: {completion_pct}% complete")
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(response, indent=2)
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }
            ]
        }
