# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Status Tracker Lambda - Get comprehensive status for clients.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')


def decimal_default(obj):
    """Helper function to serialize Decimal objects to JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SETTINGS_TABLE = os.environ['SETTINGS_TABLE']


def get_all_clients(accountant_id: str) -> List[Dict[str, Any]]:
    """Get all clients for an accountant."""
    table = dynamodb.Table(CLIENTS_TABLE)
    try:
        response = table.query(
            IndexName='accountant-index',
            KeyConditionExpression=Key('accountant_id').eq(accountant_id)
        )
        return response.get('Items', [])
    except ClientError as e:
        logger.error(f"Error querying clients: {e}")
        raise


def get_client_documents(client_id: str) -> Dict[str, Any]:
    """Get document status for a client."""
    table = dynamodb.Table(DOCUMENTS_TABLE)
    try:
        response = table.query(
            KeyConditionExpression=Key('client_id').eq(client_id)
        )
        documents = response.get('Items', [])
        required_docs = [d for d in documents if d.get('required', False)]
        
        # Count only REQUIRED documents that are received
        received_required_docs = [d for d in required_docs if d.get('received', False)]
        
        total_required = len(required_docs)
        total_received = len(received_required_docs)
        completion_pct = int((total_received / total_required) * 100) if total_required > 0 else 0
        
        # Cap at 100% to prevent display issues
        completion_pct = min(completion_pct, 100)
        
        missing_docs = [d['document_type'] for d in required_docs if not d.get('received', False)]
        
        return {
            'total_required': total_required,
            'total_received': total_received,
            'completion_percentage': completion_pct,
            'missing_documents': missing_docs
        }
    except ClientError as e:
        logger.error(f"Error getting documents: {e}")
        return {'total_required': 0, 'total_received': 0, 'completion_percentage': 0, 'missing_documents': []}


def get_followup_history(client_id: str) -> Dict[str, Any]:
    """Get follow-up history for a client."""
    table = dynamodb.Table(FOLLOWUP_TABLE)
    try:
        response = table.query(
            KeyConditionExpression=Key('client_id').eq(client_id),
            ScanIndexForward=False,
            Limit=10
        )
        followups = response.get('Items', [])
        
        if not followups:
            return {
                'followup_count': 0,
                'last_followup': None,
                'last_followup_date': None,
                'next_followup_date': None
            }
        
        last_followup = followups[0]
        return {
            'followup_count': len(followups),
            'last_followup': last_followup.get('followup_number', 0),
            'last_followup_date': last_followup.get('sent_date'),
            'next_followup_date': last_followup.get('next_followup_date'),
            'response_received': last_followup.get('response_received', False)
        }
    except ClientError as e:
        logger.error(f"Error getting follow-up history: {e}")
        return {'followup_count': 0, 'last_followup': None, 'last_followup_date': None, 'next_followup_date': None}


def calculate_risk_status(completion_pct: int, followup_count: int, 
                         last_followup_date: Optional[str], settings: Dict[str, Any]) -> str:
    """Calculate client risk status."""
    if completion_pct == 100:
        return 'complete'
    
    escalation_threshold = settings.get('escalation_threshold', 3)
    escalation_days = settings.get('escalation_days', 2)
    
    if followup_count >= escalation_threshold:
        if last_followup_date:
            last_date = datetime.fromisoformat(last_followup_date)
            days_since = (datetime.utcnow() - last_date).days
            if days_since >= escalation_days:
                return 'escalated'
        return 'at_risk'
    
    if followup_count >= (escalation_threshold - 1):
        return 'at_risk'
    
    return 'incomplete'


def calculate_days_until_escalation(followup_count: int, last_followup_date: Optional[str],
                                    settings: Dict[str, Any]) -> Optional[int]:
    """Calculate days until escalation."""
    escalation_threshold = settings.get('escalation_threshold', 3)
    escalation_days = settings.get('escalation_days', 2)
    
    if followup_count < escalation_threshold:
        return None
    
    if not last_followup_date:
        return 0
    
    last_date = datetime.fromisoformat(last_followup_date)
    escalation_date = last_date + timedelta(days=escalation_days)
    days_until = (escalation_date - datetime.utcnow()).days
    
    return max(0, days_until)


def determine_next_action(status: str, followup_count: int, next_followup_date: Optional[str]) -> str:
    """Determine next action for client."""
    if status == 'complete':
        return 'No action needed - all documents received'
    if status == 'escalated':
        return 'Requires accountant intervention - call client directly'
    if status == 'at_risk':
        if next_followup_date:
            return f"Send reminder #{followup_count + 1} on {next_followup_date[:10]}"
        return f"Send reminder #{followup_count + 1} immediately"
    if next_followup_date:
        return f"Send reminder #{followup_count + 1} on {next_followup_date[:10]}"
    return "Send initial document request"


def build_client_status(client: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """Build comprehensive status for a client."""
    client_id = client['client_id']
    doc_status = get_client_documents(client_id)
    followup_status = get_followup_history(client_id)
    
    status = calculate_risk_status(
        completion_pct=doc_status['completion_percentage'],
        followup_count=followup_status['followup_count'],
        last_followup_date=followup_status['last_followup_date'],
        settings=settings
    )
    
    days_until_escalation = calculate_days_until_escalation(
        followup_count=followup_status['followup_count'],
        last_followup_date=followup_status['last_followup_date'],
        settings=settings
    )
    
    next_action = determine_next_action(
        status=status,
        followup_count=followup_status['followup_count'],
        next_followup_date=followup_status['next_followup_date']
    )
    
    # Get detailed document list with received status
    table = dynamodb.Table(DOCUMENTS_TABLE)
    try:
        logger.info(f"Querying documents table: {DOCUMENTS_TABLE} for client_id: {client_id}")
        
        # Query with pagination to ensure we get ALL documents
        all_items = []
        last_evaluated_key = None
        page_count = 0
        
        while True:
            page_count += 1
            query_params = {
                'KeyConditionExpression': Key('client_id').eq(client_id),
                'ConsistentRead': True
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            logger.info(f"Executing query page {page_count} for client {client_id}")
            doc_response = table.query(**query_params)
            page_items = doc_response.get('Items', [])
            logger.info(f"Page {page_count} returned {len(page_items)} items")
            
            all_items.extend(page_items)
            
            last_evaluated_key = doc_response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        logger.info(f"Documents query for {client_id}: found {len(all_items)} items (with pagination, {page_count} pages)")
        
        # Include ALL documents (required and optional/uploaded)
        all_docs = [
            {
                'type': d['document_type'],
                'source': d.get('source', 'Unknown'),
                'received': d.get('received', False),
                'required': d.get('required', False),
                'received_date': d.get('received_date'),
                'file_path': d.get('file_path')
            }
            for d in all_items
        ]
        
        logger.info(f"Transformed {len(all_docs)} documents for client {client_id}")
        
        # Sort: required first, then by received status, then alphabetically
        all_docs.sort(key=lambda x: (
            not x['required'],  # Required first
            not x['received'],  # Received before missing
            x['type']  # Alphabetical
        ))
        
    except ClientError as e:
        logger.error(f"Error getting required documents: {e}", exc_info=True)
        all_docs = []
    except Exception as e:
        logger.error(f"Unexpected error getting documents: {e}", exc_info=True)
        all_docs = []
    
    return {
        'client_id': client_id,
        'client_name': client.get('client_name', 'Unknown'),
        'email': client.get('email', ''),
        'phone': client.get('phone'),
        'status': status,
        'completion_percentage': doc_status['completion_percentage'],
        'total_required': doc_status['total_required'],
        'total_received': doc_status['total_received'],
        'missing_documents': doc_status['missing_documents'],
        'required_documents': all_docs,  # Now includes ALL documents
        'followup_count': followup_status['followup_count'],
        'last_followup': followup_status['last_followup'],
        'last_followup_date': followup_status['last_followup_date'],
        'next_followup_date': followup_status['next_followup_date'],
        'days_until_escalation': days_until_escalation,
        'next_action': next_action
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for getting client status. Supports both Gateway tool calls and API Gateway requests."""
    try:
        # Detect event source: API Gateway vs AgentCore Gateway
        is_api_gateway = 'httpMethod' in event or 'requestContext' in event
        
        if is_api_gateway:
            # API Gateway event (from dashboard)
            logger.info("Processing API Gateway request")
            
            # Extract accountant_id from JWT claims (Cognito sub)
            query_params = event.get('queryStringParameters') or {}
            
            # Get accountant_id from JWT token (not query params)
            request_context = event.get('requestContext', {})
            authorizer = request_context.get('authorizer', {})
            claims = authorizer.get('claims', {})
            
            # Use Cognito sub as accountant_id
            accountant_id = claims.get('sub')
            
            if not accountant_id:
                raise ValueError("Unable to determine accountant ID from authentication token")
            
            logger.info(f"Extracted accountant_id from JWT: {accountant_id}")
            
            client_id = query_params.get('client_id') or 'all'  # Ensure we get 'all' if None
            status_filter = query_params.get('filter') or 'all'
            
            logger.info(f"API Gateway - Query params: {query_params}")
            logger.info(f"API Gateway - client_id: '{client_id}', type: {type(client_id)}, equals 'all': {client_id == 'all'}")
            
        else:
            # AgentCore Gateway tool event
            logger.info("Processing AgentCore Gateway tool call")
            delimiter = "___"
            original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
            tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
            logger.info(f"Tool invoked: {tool_name}")
            
            accountant_id = event.get('accountant_id')
            client_id = event.get('client_id', 'all')
            status_filter = event.get('filter', 'all')
        
        logger.info(f"Event: {json.dumps(event)}")
        
        if not accountant_id:
            raise ValueError("Missing required parameter: accountant_id")
        
        logger.info(f"Accountant ID: {accountant_id}, Client ID: {client_id}, Filter: {status_filter}")
        
        settings = {'escalation_threshold': 3, 'escalation_days': 2}
        
        if client_id == 'all':
            logger.info("Fetching all clients")
            clients = get_all_clients(accountant_id)
        else:
            logger.info(f"Fetching specific client: {client_id}")
            table = dynamodb.Table(CLIENTS_TABLE)
            response = table.get_item(Key={'client_id': client_id})
            if 'Item' not in response:
                raise ValueError(f"Client not found: {client_id}")
            clients = [response['Item']]
            logger.info(f"Found client: {clients[0].get('client_name')}")
        
        client_statuses = []
        for client in clients:
            client_status = build_client_status(client, settings)
            if status_filter == 'all' or client_status['status'] == status_filter:
                client_statuses.append(client_status)
        
        summary = {
            'total_clients': len(client_statuses),
            'complete': len([c for c in client_statuses if c['status'] == 'complete']),
            'incomplete': len([c for c in client_statuses if c['status'] == 'incomplete']),
            'at_risk': len([c for c in client_statuses if c['status'] == 'at_risk']),
            'escalated': len([c for c in client_statuses if c['status'] == 'escalated'])
        }
        
        priority_order = {'escalated': 0, 'at_risk': 1, 'incomplete': 2, 'complete': 3}
        client_statuses.sort(key=lambda x: priority_order.get(x['status'], 4))
        
        response_data = {
            'summary': summary,
            'clients': client_statuses,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Status retrieved for {len(client_statuses)} clients")
        
        # Return format depends on event source
        if is_api_gateway:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps(response_data, default=decimal_default)
            }
        else:
            return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps(response_data, indent=2, default=decimal_default)
                }]
            }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        
        if is_api_gateway:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            }
        else:
            return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps({
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }]
            }
