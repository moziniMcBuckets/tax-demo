# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Invoice Collection Tool

Generates invoices, tracks payments, sends reminders.
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
s3 = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle invoice collection tool calls from AgentCore Gateway."""
    try:
        body = json.loads(event.get('body', '{}'))
        tool_name = body.get('tool_name')
        parameters = body.get('parameters', {})
        org_id = event['requestContext']['authorizer']['claims'].get('sub')
        
        print(f"[TOOL] Invoice - Tool: {tool_name}, Org: {org_id}")
        
        if tool_name == 'generate_invoice':
            return generate_invoice(parameters, org_id)
        elif tool_name == 'create_payment_link':
            return create_payment_link(parameters, org_id)
        elif tool_name == 'send_invoice':
            return send_invoice(parameters, org_id)
        elif tool_name == 'check_payment_status':
            return check_payment_status(parameters, org_id)
        elif tool_name == 'send_payment_reminder':
            return send_payment_reminder(parameters, org_id)
        else:
            return {'statusCode': 400, 'body': json.dumps({'error': f'Unknown tool: {tool_name}'})}
    
    except Exception as e:
        print(f"[ERROR] Invoice tool error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


def generate_invoice(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Generate invoice PDF with service details."""
    appointment_id = params.get('appointment_id')
    line_items = params.get('line_items', [])
    tax_rate = Decimal(str(params.get('tax_rate', 0.08)))
    
    # Get appointment details
    appts_table = dynamodb.Table(os.environ['APPOINTMENTS_TABLE'])
    appt_response = appts_table.get_item(Key={'appointment_id': appointment_id, 'org_id': org_id})
    
    if 'Item' not in appt_response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Appointment not found'})}
    
    appt = appt_response['Item']
    
    # Calculate totals
    subtotal = sum(Decimal(str(item.get('amount', 0))) for item in line_items)
    tax = subtotal * tax_rate
    total = subtotal + tax
    
    # Generate invoice ID and number
    invoice_id = f"inv_{int(datetime.utcnow().timestamp() * 1000)}"
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{invoice_id[-6:]}"
    due_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    # Store in DynamoDB
    invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE'])
    invoices_table.put_item(Item={
        'invoice_id': invoice_id,
        'org_id': org_id,
        'appointment_id': appointment_id,
        'customer_name': appt.get('customer_name', ''),
        'customer_email': appt.get('customer_email', ''),
        'invoice_number': invoice_number,
        'invoice_date': datetime.utcnow().isoformat(),
        'due_date': due_date,
        'line_items': line_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'status': 'draft',
        'reminders_sent': [],
        'created_at': datetime.utcnow().isoformat()
    })
    
    print(f"[INVOICE] Generated {invoice_id}: ${float(total):.2f}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'total': float(total),
            'due_date': due_date
        }, default=str)
    }


def create_payment_link(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Create Stripe payment link for invoice."""
    invoice_id = params.get('invoice_id')
    
    # Get invoice details
    invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE'])
    response = invoices_table.get_item(Key={'invoice_id': invoice_id, 'org_id': org_id})
    
    if 'Item' not in response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Invoice not found'})}
    
    invoice = response['Item']
    
    # Generate payment link (simplified - would use Stripe API in production)
    payment_link = f"https://pay.raincity.ai/{invoice_id}"
    
    # Update invoice with payment link
    invoices_table.update_item(
        Key={'invoice_id': invoice_id, 'org_id': org_id},
        UpdateExpression='SET payment_link = :link',
        ExpressionAttributeValues={':link': payment_link}
    )
    
    print(f"[PAYMENT] Created payment link for {invoice_id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'payment_link': payment_link})
    }


def send_invoice(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Send invoice via email with PDF and payment link."""
    invoice_id = params.get('invoice_id')
    
    # Get invoice details
    invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE'])
    response = invoices_table.get_item(Key={'invoice_id': invoice_id, 'org_id': org_id})
    
    if 'Item' not in response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Invoice not found'})}
    
    invoice = response['Item']
    
    # Format invoice email
    line_items_text = '\n'.join([
        f"{item.get('description', 'Service')}: ${float(item.get('amount', 0)):.2f}"
        for item in invoice.get('line_items', [])
    ])
    
    due_date_formatted = datetime.fromisoformat(invoice['due_date']).strftime('%B %d, %Y')
    
    email_body = f"""Invoice {invoice['invoice_number']}

{line_items_text}

Subtotal: ${float(invoice['subtotal']):.2f}
Tax: ${float(invoice['tax']):.2f}
Total: ${float(invoice['total']):.2f}

Pay online: {invoice.get('payment_link', 'TBD')}
Due: {due_date_formatted} (Net 30)

Thank you for your business!
- RainCity"""
    
    # Send email
    ses.send_email(
        Source=os.environ.get('FROM_EMAIL', 'noreply@raincity.ai'),
        Destination={'ToAddresses': [invoice['customer_email']]},
        Message={
            'Subject': {'Data': f"Invoice {invoice['invoice_number']}"},
            'Body': {'Text': {'Data': email_body}}
        }
    )
    
    # Update status to sent
    invoices_table.update_item(
        Key={'invoice_id': invoice_id, 'org_id': org_id},
        UpdateExpression='SET #status = :status, sent_at = :sent_at',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'sent',
            ':sent_at': datetime.utcnow().isoformat()
        }
    )
    
    print(f"[INVOICE] Sent {invoice_id} to {invoice['customer_email']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'sent': True, 'invoice_id': invoice_id})
    }


def check_payment_status(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Check if invoice has been paid."""
    invoice_id = params.get('invoice_id')
    
    invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE'])
    response = invoices_table.get_item(Key={'invoice_id': invoice_id, 'org_id': org_id})
    
    if 'Item' not in response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Invoice not found'})}
    
    invoice = response['Item']
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'invoice_id': invoice_id,
            'status': invoice.get('status', 'unknown'),
            'paid': invoice.get('status') == 'paid',
            'paid_date': invoice.get('paid_date')
        })
    }


def send_payment_reminder(params: Dict[str, Any], org_id: str) -> Dict[str, Any]:
    """Send payment reminder for overdue invoice."""
    invoice_id = params.get('invoice_id')
    reminder_type = params.get('reminder_type', 'gentle')
    
    invoices_table = dynamodb.Table(os.environ['INVOICES_TABLE'])
    response = invoices_table.get_item(Key={'invoice_id': invoice_id, 'org_id': org_id})
    
    if 'Item' not in response:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Invoice not found'})}
    
    invoice = response['Item']
    
    # Different messages based on reminder type
    if reminder_type == 'gentle':
        message = f"Friendly reminder: Invoice {invoice['invoice_number']} for ${float(invoice['total']):.2f} is due soon. Pay online: {invoice.get('payment_link', 'TBD')}"
    elif reminder_type == 'firm':
        message = f"Payment reminder: Invoice {invoice['invoice_number']} for ${float(invoice['total']):.2f} is now overdue. Please remit payment: {invoice.get('payment_link', 'TBD')}"
    else:  # final
        message = f"FINAL NOTICE: Invoice {invoice['invoice_number']} for ${float(invoice['total']):.2f} is seriously overdue. Please contact us immediately to arrange payment."
    
    # Send email
    ses.send_email(
        Source=os.environ.get('FROM_EMAIL', 'noreply@raincity.ai'),
        Destination={'ToAddresses': [invoice['customer_email']]},
        Message={
            'Subject': {'Data': f"Payment Reminder - Invoice {invoice['invoice_number']}"},
            'Body': {'Text': {'Data': message}}
        }
    )
    
    # Log reminder
    reminders = invoice.get('reminders_sent', [])
    reminders.append(datetime.utcnow().isoformat())
    
    invoices_table.update_item(
        Key={'invoice_id': invoice_id, 'org_id': org_id},
        UpdateExpression='SET reminders_sent = :reminders',
        ExpressionAttributeValues={':reminders': reminders}
    )
    
    print(f"[REMINDER] Sent {reminder_type} reminder for {invoice_id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'sent': True, 'reminder_type': reminder_type})
    }
