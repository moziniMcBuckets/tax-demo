# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Usage Tracking Utility

Tracks operations for billing and cost allocation.
Used by all Lambda functions to log usage.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()

# Pricing constants (USD)
PRICING = {
    'agent_invocation': 0.003,
    'gateway_tool_call': 0.0001,
    'email_sent': 0.0001,
    'sms_sent': 0.00645,
    'document_storage_gb_month': 0.023,
    'client_per_month': 0.10,
    'api_request': 0.0000035,
}


def track_usage(
    accountant_id: str,
    operation: str,
    resource_type: str,
    quantity: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Track usage for billing purposes.
    
    Args:
        accountant_id: Accountant/tenant identifier
        operation: Operation performed (send_email, agent_invocation, etc.)
        resource_type: Type of resource used
        quantity: Amount used (1 email, 2.5 GB, etc.)
        metadata: Additional context (client_id, document_type, etc.)
    """
    usage_table_name = os.environ.get('USAGE_TABLE')
    if not usage_table_name:
        logger.warning("USAGE_TABLE not configured, skipping usage tracking")
        return
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(usage_table_name)
        
        timestamp = datetime.utcnow().isoformat()
        month = timestamp[:7]  # YYYY-MM format
        
        # Calculate estimated cost
        unit_cost = PRICING.get(resource_type, 0.0)
        estimated_cost = unit_cost * quantity
        
        # Create usage record
        record = {
            'accountant_id': accountant_id,
            'timestamp': timestamp,
            'month': month,
            'operation': operation,
            'resource_type': resource_type,
            'quantity': quantity,
            'unit_cost': unit_cost,
            'estimated_cost': estimated_cost,
            'metadata': metadata or {}
        }
        
        table.put_item(Item=record)
        logger.info(f"Tracked usage: {operation} for {accountant_id}, cost: ${estimated_cost:.6f}")
        
    except ClientError as e:
        logger.error(f"Error tracking usage: {e}")
        # Don't fail the operation if usage tracking fails
    except Exception as e:
        logger.error(f"Unexpected error tracking usage: {e}")


def get_monthly_usage(accountant_id: str, month: str) -> Dict[str, Any]:
    """
    Get usage summary for an accountant for a specific month.
    
    Args:
        accountant_id: Accountant identifier
        month: Month in YYYY-MM format
    
    Returns:
        Dictionary with usage summary and total cost
    """
    usage_table_name = os.environ.get('USAGE_TABLE')
    if not usage_table_name:
        return {'error': 'Usage tracking not configured'}
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(usage_table_name)
        
        response = table.query(
            IndexName='month-index',
            KeyConditionExpression='accountant_id = :aid AND #month = :month',
            ExpressionAttributeNames={'#month': 'month'},
            ExpressionAttributeValues={':aid': accountant_id, ':month': month}
        )
        
        items = response.get('Items', [])
        
        # Aggregate by resource type
        usage_by_type = {}
        total_cost = 0.0
        
        for item in items:
            resource_type = item['resource_type']
            quantity = float(item.get('quantity', 0))
            cost = float(item.get('estimated_cost', 0))
            
            if resource_type not in usage_by_type:
                usage_by_type[resource_type] = {
                    'quantity': 0,
                    'cost': 0.0,
                    'count': 0
                }
            
            usage_by_type[resource_type]['quantity'] += quantity
            usage_by_type[resource_type]['cost'] += cost
            usage_by_type[resource_type]['count'] += 1
            total_cost += cost
        
        return {
            'accountant_id': accountant_id,
            'month': month,
            'total_cost': round(total_cost, 4),
            'usage_by_type': usage_by_type,
            'total_operations': len(items)
        }
        
    except ClientError as e:
        logger.error(f"Error getting monthly usage: {e}")
        return {'error': str(e)}
