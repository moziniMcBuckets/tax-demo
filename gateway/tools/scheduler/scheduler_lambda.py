# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Scheduler Tool

Checks availability, books appointments, sends confirmations.
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
sns = boto3.client('sns')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle scheduler tool calls from AgentCore Gateway."""
    try:
        body = json.loads(event.get('body', '{}'))
        tool_name = body.get('tool_name')
        parameters = body.get('parameters', {})
        org_id = event['requestContext']['authorizer']['claims'].get('sub')
        
        print(f"[TOOL] Scheduler - Tool: {tool_name}, Org: {org_id}")
        
        if tool_name == 'check_availability':
            return check_availability(parameters, org_id)
        elif tool_name == 'book_appointment':
            return book_appointment(parameters, org_id)
        elif tool_name == 'send_confirmation':
            return send_confirmation(parameters, org_id)
        else:
            return {'statusCode': 400, 'body': json.dumps({'error': f'Unknown tool: {tool_name}'})}
    
    except Exception as e:
        print(f"[ERROR] Scheduler tool error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


def check_availability(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Check technician availability."""
    start_date = params.get('start_date')
    service_type = params.get('service_type')
    location = params.get('location')
    
    # Query technicians with required skills
    techs_table = dynamodb.Table(os.environ['TECHNICIANS_TABLE'])
    response = techs_table.query(
        IndexName='org_id-status-index',
        KeyConditionExpression='org_id = :org AND #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':org': org_id, ':status': 'active'}
    )
    
    # Filter by skills (simplified - would check calendar in production)
    available_slots = []
    for tech in response.get('Items', []):
        if service_type.lower() in [s.lower() for s in tech.get('skills', [])]:
            # Generate sample slots (would query calendar API in production)
            base_time = datetime.fromisoformat(start_date) if start_date else datetime.utcnow()
            for hour in [14, 16]:  # 2pm, 4pm
                available_slots.append({
                    'time': (base_time.replace(hour=hour, minute=0)).isoformat(),
                    'technician_id': tech['technician_id'],
                    'technician_name': tech['name'],
                    'skills': tech['skills']
                })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'available_slots': available_slots,
            'count': len(available_slots)
        })
    }


def book_appointment(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Book appointment in calendar and database."""
    lead_id = params.get('lead_id')
    scheduled_time = params.get('scheduled_time')
    technician_id = params.get('technician_id')
    service_type = params.get('service_type')
    customer_address = params.get('customer_address', '')
    
    # Get lead details
    leads_table = dynamodb.Table(os.environ['LEADS_TABLE'])
    lead_response = leads_table.get_item(Key={'lead_id': lead_id, 'org_id': org_id})
    
    if 'Item' not in lead_response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Lead not found'})}
    
    lead = lead_response['Item']
    
    # Create appointment
    appointment_id = f"appt_{int(datetime.utcnow().timestamp() * 1000)}"
    appts_table = dynamodb.Table(os.environ['APPOINTMENTS_TABLE'])
    
    appts_table.put_item(Item={
        'appointment_id': appointment_id,
        'org_id': org_id,
        'lead_id': lead_id,
        'customer_name': lead.get('name', ''),
        'customer_email': lead.get('email', ''),
        'customer_phone': lead.get('phone', ''),
        'customer_address': customer_address,
        'service_type': service_type,
        'scheduled_time': scheduled_time,
        'technician_id': technician_id,
        'status': 'scheduled',
        'reminders_sent': [],
        'created_at': datetime.utcnow().isoformat()
    })
    
    # Update lead status
    leads_table.update_item(
        Key={'lead_id': lead_id, 'org_id': org_id},
        UpdateExpression='SET #status = :status, appointment_id = :appt_id',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'scheduled', ':appt_id': appointment_id}
    )
    
    print(f"[BOOK] Appointment {appointment_id} booked for {scheduled_time}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'appointment_id': appointment_id,
            'scheduled_time': scheduled_time,
            'status': 'scheduled'
        })
    }


def send_confirmation(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Send appointment confirmation via email and SMS."""
    appointment_id = params.get('appointment_id')
    
    # Get appointment details
    appts_table = dynamodb.Table(os.environ['APPOINTMENTS_TABLE'])
    response = appts_table.get_item(Key={'appointment_id': appointment_id, 'org_id': org_id})
    
    if 'Item' not in response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Appointment not found'})}
    
    appt = response['Item']
    
    # Get technician name
    techs_table = dynamodb.Table(os.environ['TECHNICIANS_TABLE'])
    tech_response = techs_table.get_item(
        Key={'technician_id': appt['technician_id'], 'org_id': org_id}
    )
    tech_name = tech_response.get('Item', {}).get('name', 'Technician')
    
    # Format confirmation message
    scheduled_dt = datetime.fromisoformat(appt['scheduled_time'])
    confirmation_msg = f"""Appointment Confirmed! ✓

Technician: {tech_name}
Time: {scheduled_dt.strftime('%A, %B %d at %I:%M %p')}
Service: {appt['service_type']}
Address: {appt.get('customer_address', 'TBD')}

{tech_name} will call 15 minutes before arrival.

Need to reschedule? Reply to this message.

- RainCity AI"""
    
    # Send email if available
    if appt.get('customer_email'):
        ses.send_email(
            Source=os.environ.get('FROM_EMAIL', 'noreply@raincity.ai'),
            Destination={'ToAddresses': [appt['customer_email']]},
            Message={
                'Subject': {'Data': 'Appointment Confirmed'},
                'Body': {'Text': {'Data': confirmation_msg}}
            }
        )
    
    # Send SMS if available
    if appt.get('customer_phone'):
        phone = appt['customer_phone']
        if not phone.startswith('+'):
            phone = f'+1{phone.replace("-", "").replace(" ", "")}'
        sns.publish(PhoneNumber=phone, Message=confirmation_msg)
    
    print(f"[CONFIRM] Confirmation sent for {appointment_id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'sent': True,
            'appointment_id': appointment_id
        })
    }
