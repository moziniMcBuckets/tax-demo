# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Billing Lambda

Calculates usage and costs for accountants.
Provides monthly usage reports and cost breakdowns.
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

dynamodb = boto3.resource('dynamodb')

USAGE_TABLE = os.environ['USAGE_TABLE']


def get_monthly_usage(accountant_id: str, month: str) -> Dict[str, Any]:
    """Get usage summary for a month."""
    table = dynamodb.Table(USAGE_TABLE)
    
    try:
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
                    'operations': 0
                }
            
            usage_by_type[resource_type]['quantity'] += quantity
            usage_by_type[resource_type]['cost'] += cost
            usage_by_type[resource_type]['operations'] += 1
            total_cost += cost
        
        return {
            'accountant_id': accountant_id,
            'month': month,
            'total_cost': round(total_cost, 4),
            'usage_by_type': usage_by_type,
            'total_operations': len(items),
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except ClientError as e:
        logger.error(f"Error getting monthly usage: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for billing operations.
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        API Gateway response with usage data
    """
    try:
        logger.info(f"Billing request: {json.dumps(event)}")
        
        # Extract accountant_id from JWT
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
        
        # Get month from query params (default to current month)
        query_params = event.get('queryStringParameters') or {}
        month = query_params.get('month', datetime.utcnow().strftime('%Y-%m'))
        
        # Get usage data
        usage_data = get_monthly_usage(accountant_id, month)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps(usage_data)
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
                'error': str(e),
                'error_type': type(e).__name__
            })
        }
