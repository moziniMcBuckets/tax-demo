# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Requirement Manager Lambda - Add, update, or remove required documents for clients.
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

dynamodb = boto3.resource('dynamodb')

CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']

STANDARD_DOCUMENT_TYPES = [
    'W-2', '1099-INT', '1099-DIV', '1099-MISC', '1099-NEC', '1099-B', '1099-R',
    '1099-G', '1099-K', 'Schedule K-1', 'Mortgage Interest Statement (1098)',
    'Student Loan Interest (1098-E)', 'Tuition Statement (1098-T)',
    'Health Insurance Form (1095-A/B/C)', 'Charitable Donation Receipts',
    'Medical Expense Receipts', 'Business Expense Receipts', 'Property Tax Statement',
    'Prior Year Tax Return', 'Estimated Tax Payment Records',
]


def validate_client_exists(client_id: str) -> bool:
    """Verify that client exists in database."""
    table = dynamodb.Table(CLIENTS_TABLE)
    try:
        response = table.get_item(Key={'client_id': client_id})
        return 'Item' in response
    except ClientError as e:
        logger.error(f"Error checking client existence: {e}")
        return False


def validate_document_type(document_type: str) -> bool:
    """Validate document type against standard types."""
    if document_type in STANDARD_DOCUMENT_TYPES:
        return True
    if len(document_type) > 100:
        return False
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -()')
    return all(c in allowed_chars for c in document_type)


def add_document_requirement(client_id: str, tax_year: int, document_type: str,
                            source: str, required: bool) -> None:
    """Add or update document requirement."""
    table = dynamodb.Table(DOCUMENTS_TABLE)
    try:
        table.put_item(
            Item={
                'client_id': client_id,
                'document_type': document_type,
                'tax_year': tax_year,
                'source': source,
                'required': required,
                'received': False,
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
            }
        )
        logger.info(f"Added requirement: {document_type} for client {client_id}")
    except ClientError as e:
        logger.error(f"Error adding document requirement: {e}")
        raise


def remove_document_requirement(client_id: str, document_type: str) -> None:
    """Remove document requirement."""
    table = dynamodb.Table(DOCUMENTS_TABLE)
    try:
        table.delete_item(Key={'client_id': client_id, 'document_type': document_type})
        logger.info(f"Removed requirement: {document_type} for client {client_id}")
    except ClientError as e:
        logger.error(f"Error removing document requirement: {e}")
        raise


def update_document_requirement(client_id: str, document_type: str, updates: Dict[str, Any]) -> None:
    """Update existing document requirement."""
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    update_expr_parts = []
    expr_attr_values = {}
    expr_attr_names = {}
    
    for key, value in updates.items():
        attr_name = f"#{key}"
        attr_value = f":{key}"
        update_expr_parts.append(f"{attr_name} = {attr_value}")
        expr_attr_names[attr_name] = key
        expr_attr_values[attr_value] = value
    
    update_expr_parts.append("#last_updated = :last_updated")
    expr_attr_names["#last_updated"] = "last_updated"
    expr_attr_values[":last_updated"] = datetime.utcnow().isoformat()
    
    update_expression = "SET " + ", ".join(update_expr_parts)
    
    try:
        table.update_item(
            Key={'client_id': client_id, 'document_type': document_type},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        logger.info(f"Updated requirement: {document_type} for client {client_id}")
    except ClientError as e:
        logger.error(f"Error updating document requirement: {e}")
        raise


def get_current_requirements(client_id: str, tax_year: int) -> List[Dict[str, Any]]:
    """Get current document requirements for client."""
    table = dynamodb.Table(DOCUMENTS_TABLE)
    try:
        response = table.query(
            KeyConditionExpression='client_id = :cid',
            FilterExpression='tax_year = :year',
            ExpressionAttributeValues={':cid': client_id, ':year': tax_year}
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error getting current requirements: {e}")
        return []


def apply_standard_requirements(client_id: str, tax_year: int, client_type: str = 'individual') -> int:
    """Apply standard document requirements based on client type."""
    standard_requirements = {
        'individual': [
            ('W-2', 'All Employers', True),
            ('1099-INT', 'All Banks', False),
            ('1099-DIV', 'All Investment Accounts', False),
            ('Prior Year Tax Return', 'IRS', True),
        ],
        'self_employed': [
            ('1099-NEC', 'All Clients', True),
            ('1099-MISC', 'All Sources', False),
            ('Business Expense Receipts', 'Various', True),
            ('Prior Year Tax Return', 'IRS', True),
        ],
        'business': [
            ('1099-NEC', 'All Contractors', True),
            ('Business Expense Receipts', 'Various', True),
            ('Prior Year Tax Return', 'IRS', True),
        ]
    }
    
    requirements = standard_requirements.get(client_type, standard_requirements['individual'])
    count = 0
    for doc_type, source, required in requirements:
        try:
            add_document_requirement(client_id, tax_year, doc_type, source, required)
            count += 1
        except Exception as e:
            logger.error(f"Error adding standard requirement {doc_type}: {e}")
    return count


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for managing document requirements."""
    try:
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Tool invoked: {tool_name}")
        logger.info(f"Event: {json.dumps(event)}")
        
        client_id = event.get('client_id')
        tax_year = event.get('tax_year')
        operation = event.get('operation', 'add')
        documents = event.get('documents', [])
        
        if not client_id or not tax_year:
            raise ValueError("Missing required parameters: client_id, tax_year")
        
        if not validate_client_exists(client_id):
            raise ValueError(f"Client not found: {client_id}")
        
        results = {
            'client_id': client_id,
            'tax_year': tax_year,
            'operation': operation,
            'success': True,
            'documents_processed': 0,
            'errors': []
        }
        
        if operation == 'apply_standard':
            client_type = event.get('client_type', 'individual')
            count = apply_standard_requirements(client_id, tax_year, client_type)
            results['documents_processed'] = count
            results['message'] = f"Applied {count} standard requirements for {client_type} client"
        
        elif operation == 'add':
            for doc in documents:
                doc_type = doc.get('document_type')
                if not doc_type or not validate_document_type(doc_type):
                    results['errors'].append(f"Invalid document type: {doc_type}")
                    continue
                try:
                    add_document_requirement(
                        client_id, tax_year, doc_type,
                        doc.get('source', 'Unknown'), doc.get('required', True)
                    )
                    results['documents_processed'] += 1
                except Exception as e:
                    results['errors'].append(f"Error adding {doc_type}: {str(e)}")
        
        elif operation == 'remove':
            for doc in documents:
                doc_type = doc.get('document_type')
                if not doc_type:
                    results['errors'].append("Missing document_type")
                    continue
                try:
                    remove_document_requirement(client_id, doc_type)
                    results['documents_processed'] += 1
                except Exception as e:
                    results['errors'].append(f"Error removing {doc_type}: {str(e)}")
        
        elif operation == 'update':
            for doc in documents:
                doc_type = doc.get('document_type')
                if not doc_type:
                    results['errors'].append("Missing document_type")
                    continue
                updates = {k: v for k, v in doc.items() if k in ['source', 'required', 'received']}
                if not updates:
                    results['errors'].append(f"No updates specified for {doc_type}")
                    continue
                try:
                    update_document_requirement(client_id, doc_type, updates)
                    results['documents_processed'] += 1
                except Exception as e:
                    results['errors'].append(f"Error updating {doc_type}: {str(e)}")
        else:
            raise ValueError(f"Invalid operation: {operation}")
        
        current_requirements = get_current_requirements(client_id, tax_year)
        results['total_requirements'] = len(current_requirements)
        results['current_requirements'] = [
            {
                'document_type': req['document_type'],
                'source': req.get('source', 'Unknown'),
                'required': req.get('required', False),
                'received': req.get('received', False)
            }
            for req in current_requirements
        ]
        results['updated_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Processed {results['documents_processed']} documents for client {client_id}")
        
        return {'content': [{'type': 'text', 'text': json.dumps(results, indent=2)}]}
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {'content': [{'type': 'text', 'text': json.dumps({
            'success': False, 'error': str(e), 'error_type': type(e).__name__
        })}]}
