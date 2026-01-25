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
        received_docs = [d for d in documents if d.get('received', False)]
        
        total_required = len(required_docs)
        total_received = len(received_docs)
        completion_pct = int((total_received / total_required) * 100) if total_required > 0 else 0
        
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
    
    return {
        'client_id': client_id,
        'client_name': client.get('client_name', 'Unknown'),
        'email': client.get('email', ''),
        'status': status,
        'completion_percentage': doc_status['completion_percentage'],
        'total_required': doc_status['total_required'],
        'total_received': doc_status['total_received'],
        'missing_documents': doc_status['missing_documents'],
        'followup_count': followup_status['followup_count'],
        'last_followup': followup_status['last_followup'],
        'last_followup_date': followup_status['last_followup_date'],
        'next_followup_date': followup_status['next_followup_date'],
        'days_until_escalation': days_until_escalation,
        'next_action': next_action
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for getting client status."""
    try:
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Tool invoked: {tool_name}")
        logger.info(f"Event: {json.dumps(event)}")
        
        accountant_id = event.get('accountant_id')
        client_id = event.get('client_id', 'all')
        status_filter = event.get('filter', 'all')
        
        if not accountant_id:
            raise ValueError("Missing required parameter: accountant_id")
        
        settings = {'escalation_threshold': 3, 'escalation_days': 2}
        
        if client_id == 'all':
            clients = get_all_clients(accountant_id)
        else:
            table = dynamodb.Table(CLIENTS_TABLE)
            response = table.get_item(Key={'client_id': client_id})
            if 'Item' not in response:
                raise ValueError(f"Client not found: {client_id}")
            clients = [response['Item']]
        
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
        
        response = {
            'summary': summary,
            'clients': client_statuses,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Status retrieved for {len(client_statuses)} clients")
        
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps(response, indent=2, default=decimal_default)
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps({
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            }]
        }
