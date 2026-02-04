# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Lead Response Tool

Monitors inquiries, qualifies leads, sends responses.
Handles email, SMS, and web form submissions.
"""

import boto3
import json
import os
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
sns = boto3.client('sns')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle lead response tool calls from AgentCore Gateway.
    
    Args:
        event: Tool call from Gateway with tool_name and parameters
        context: Lambda context
    
    Returns:
        Tool response
    """
    try:
        # Extract tool name and parameters from Gateway
        body = json.loads(event.get('body', '{}'))
        tool_name = body.get('tool_name')
        parameters = body.get('parameters', {})
        
        # Extract org_id from JWT token (set by Gateway)
        org_id = event['requestContext']['authorizer']['claims'].get('sub')
        
        print(f"[TOOL] Lead Response - Tool: {tool_name}, Org: {org_id}")
        
        # Route to appropriate handler
        if tool_name == 'qualify_lead':
            return qualify_lead(parameters, org_id)
        elif tool_name == 'send_response':
            return send_response(parameters, org_id)
        elif tool_name == 'monitor_email':
            return monitor_email(parameters, org_id)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown tool: {tool_name}'})
            }
    
    except Exception as e:
        print(f"[ERROR] Lead Response tool error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def qualify_lead(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """
    Qualify and score a lead based on criteria.
    
    Args:
        params: Lead details (name, email, phone, service_needed, urgency, budget, location)
        org_id: Organization ID
    
    Returns:
        Qualification result with score and lead_id
    """
    # Extract lead details
    name = params.get('name', '')
    email = params.get('email', '')
    phone = params.get('phone', '')
    service_needed = params.get('service_needed', '')
    urgency = params.get('urgency', 'flexible')
    budget = params.get('budget', '')
    location = params.get('location', '')
    source = params.get('source', 'unknown')
    
    # Qualification scoring logic
    score = 0
    reasons = []
    
    # Has contact info? +3 points
    if email or phone:
        score += 3
        reasons.append("Has contact information")
    else:
        reasons.append("Missing contact information")
    
    # Has service need? +2 points
    if service_needed:
        score += 2
        reasons.append(f"Service needed: {service_needed}")
    else:
        reasons.append("Service need unclear")
    
    # Urgency? +2 points for emergency, +1 for this_week
    if urgency == 'emergency':
        score += 2
        reasons.append("Emergency service (high priority)")
    elif urgency == 'this_week':
        score += 1
        reasons.append("Needs service this week")
    
    # Has budget? +2 points
    if budget:
        score += 2
        reasons.append(f"Budget provided: {budget}")
    
    # Has location? +1 point
    if location:
        score += 1
        reasons.append("Location provided")
    
    # Determine if qualified (score ≥ 7)
    qualified = score >= 7
    
    # Generate lead_id
    lead_id = f"lead_{int(datetime.utcnow().timestamp() * 1000)}"
    
    # Store in DynamoDB
    leads_table = dynamodb.Table(os.environ['LEADS_TABLE'])
    
    lead_item = {
        'lead_id': lead_id,
        'org_id': org_id,
        'name': name,
        'email': email,
        'phone': phone,
        'service_needed': service_needed,
        'urgency': urgency,
        'budget': budget,
        'location': location,
        'source': source,
        'status': 'qualified' if qualified else 'not_qualified',
        'qualification_score': Decimal(str(score)),
        'qualification_reasons': reasons,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    leads_table.put_item(Item=lead_item)
    
    print(f"[QUALIFY] Lead {lead_id}: score={score}, qualified={qualified}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'lead_id': lead_id,
            'qualified': qualified,
            'score': score,
            'reasons': reasons,
            'message': f"Lead scored {score}/10. {'Qualified for scheduling' if qualified else 'Not qualified'}"
        })
    }


def send_response(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """
    Send response to lead via email or SMS.
    
    Args:
        params: Response details (lead_id, message, contact_method)
        org_id: Organization ID
    
    Returns:
        Send status
    """
    lead_id = params.get('lead_id')
    message = params.get('message')
    contact_method = params.get('contact_method', 'email')
    
    if not lead_id or not message:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing lead_id or message'})
        }
    
    # Get lead details from database
    leads_table = dynamodb.Table(os.environ['LEADS_TABLE'])
    response = leads_table.get_item(
        Key={'lead_id': lead_id, 'org_id': org_id}
    )
    
    if 'Item' not in response:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Lead not found'})
        }
    
    lead = response['Item']
    customer_email = lead.get('email')
    customer_phone = lead.get('phone')
    customer_name = lead.get('name', 'Customer')
    
    # Send via requested method
    if contact_method == 'email' and customer_email:
        send_email_response(customer_email, customer_name, message)
        sent_to = customer_email
    elif contact_method == 'sms' and customer_phone:
        send_sms_response(customer_phone, message)
        sent_to = customer_phone
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'No {contact_method} address for lead'})
        }
    
    # Update lead with response sent
    leads_table.update_item(
        Key={'lead_id': lead_id, 'org_id': org_id},
        UpdateExpression='SET last_response_at = :timestamp, #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':timestamp': datetime.utcnow().isoformat(),
            ':status': 'contacted'
        }
    )
    
    print(f"[RESPONSE] Sent {contact_method} to {sent_to}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'sent': True,
            'to': sent_to,
            'method': contact_method,
            'timestamp': datetime.utcnow().isoformat()
        })
    }


def send_email_response(email: str, name: str, message: str) -> None:
    """
    Send email response via SES.
    
    Args:
        email: Customer email address
        name: Customer name
        message: Message to send
    """
    from_email = os.environ.get('FROM_EMAIL', 'noreply@raincity.ai')
    
    ses.send_email(
        Source=from_email,
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': 'Re: Your Service Request'},
            'Body': {
                'Text': {'Data': f"Hi {name},\n\n{message}\n\nBest regards,\nRainCity AI Assistant"}
            }
        }
    )


def send_sms_response(phone: str, message: str) -> None:
    """
    Send SMS response via SNS.
    
    Args:
        phone: Customer phone number
        message: Message to send
    """
    # Format phone number for SNS
    if not phone.startswith('+'):
        phone = f'+1{phone.replace("-", "").replace(" ", "")}'
    
    sns.publish(
        PhoneNumber=phone,
        Message=message
    )


def monitor_email(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """
    Monitor email inbox for new inquiries (placeholder for webhook).
    
    This would typically be triggered by Gmail API webhook or polling.
    For now, returns status.
    
    Args:
        params: Monitoring parameters
        org_id: Organization ID
    
    Returns:
        Monitoring status
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'monitoring': True,
            'org_id': org_id,
            'message': 'Email monitoring active'
        })
    }
