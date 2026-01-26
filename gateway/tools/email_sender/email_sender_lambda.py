# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Email Sender Lambda - Sends personalized follow-up emails via AWS SES.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError

# Add common layer to path
sys.path.insert(0, '/opt/python')
try:
    from usage_tracker import track_usage
except ImportError:
    # Fallback if layer not available
    def track_usage(*args, **kwargs):
        pass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SETTINGS_TABLE = os.environ['SETTINGS_TABLE']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']


def get_client_info(client_id: str) -> Dict[str, Any]:
    """Get client information from DynamoDB."""
    table = dynamodb.Table(CLIENTS_TABLE)
    try:
        response = table.get_item(Key={'client_id': client_id})
        if 'Item' not in response:
            raise ValueError(f"Client not found: {client_id}")
        return response['Item']
    except ClientError as e:
        logger.error(f"Error getting client info: {e}")
        raise


def get_default_template(followup_number: int) -> Dict[str, str]:
    """Get default email template."""
    templates = {
        1: {
            'subject': 'Documents needed for your {tax_year} tax return',
            'body': '''Dear {client_name},

I hope this email finds you well. I'm reaching out regarding your {tax_year} tax return.

To complete your return, I still need the following documents:

{missing_documents_list}

Please upload these documents to your secure client portal at your earliest convenience.

Thank you for your prompt attention to this matter.

Best regards,
{accountant_name}
{accountant_firm}'''
        },
        2: {
            'subject': 'Reminder: Documents still needed for your {tax_year} tax return',
            'body': '''Dear {client_name},

This is a friendly reminder that I'm still waiting for the following documents:

{missing_documents_list}

The tax filing deadline is approaching. Please upload these documents as soon as possible.

Best regards,
{accountant_name}
{accountant_firm}'''
        },
        3: {
            'subject': 'URGENT: Documents needed to avoid tax filing delays',
            'body': '''Dear {client_name},

This is my third request for the following documents:

{missing_documents_list}

Without these documents, I cannot file your return on time, which may result in penalties.

Please call me directly at {accountant_phone}.

Sincerely,
{accountant_name}
{accountant_firm}'''
        }
    }
    return templates.get(followup_number, templates[1])


def format_missing_documents(missing_docs: List[str]) -> str:
    """Format missing documents list for email."""
    if not missing_docs:
        return "None - all documents received!"
    return "\n".join([f"{i}. {doc}" for i, doc in enumerate(missing_docs, 1)])


def personalize_email(template: Dict[str, str], client_info: Dict[str, Any], 
                      missing_docs: List[str], tax_year: int) -> Dict[str, str]:
    """Personalize email template with client data."""
    replacements = {
        '{client_name}': client_info.get('client_name', 'Valued Client'),
        '{tax_year}': str(tax_year),
        '{missing_documents_list}': format_missing_documents(missing_docs),
        '{accountant_name}': client_info.get('accountant_name', 'Your Accountant'),
        '{accountant_firm}': client_info.get('accountant_firm', ''),
        '{accountant_phone}': client_info.get('accountant_phone', ''),
    }
    
    subject = template['subject']
    body = template['body']
    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)
    
    return {'subject': subject, 'body': body}


def send_email_via_ses(to_email: str, subject: str, body: str) -> str:
    """Send email via AWS SES."""
    try:
        response = ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}
            }
        )
        message_id = response['MessageId']
        logger.info(f"Email sent successfully: {message_id}")
        return message_id
    except ClientError as e:
        logger.error(f"Error sending email via SES: {e}")
        raise


def log_followup(client_id: str, followup_number: int, email_subject: str,
                email_body: str, missing_docs: List[str], accountant_id: str) -> str:
    """Log follow-up to DynamoDB."""
    table = dynamodb.Table(FOLLOWUP_TABLE)
    followup_id = f"fu_{int(datetime.utcnow().timestamp())}"
    sent_date = datetime.utcnow().isoformat()
    next_followup = (datetime.utcnow() + timedelta(days=7)).isoformat()
    
    try:
        table.put_item(
            Item={
                'client_id': client_id,
                'followup_id': followup_id,
                'followup_number': followup_number,
                'sent_date': sent_date,
                'email_subject': email_subject,
                'email_body': email_body,
                'documents_requested': missing_docs,
                'response_received': False,
                'next_followup_date': next_followup,
                'escalation_triggered': False,
                'accountant_id': accountant_id
            }
        )
        logger.info(f"Follow-up logged: {followup_id}")
        return followup_id
    except ClientError as e:
        logger.error(f"Error logging follow-up: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for sending follow-up emails."""
    try:
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Tool invoked: {tool_name}")
        logger.info(f"Event: {json.dumps(event)}")
        
        client_id = event.get('client_id')
        missing_documents = event.get('missing_documents', [])
        followup_number = event.get('followup_number', 1)
        custom_message = event.get('custom_message')
        
        if not client_id or not missing_documents:
            raise ValueError("Missing required parameters: client_id, missing_documents")
        
        client_info = get_client_info(client_id)
        accountant_id = client_info.get('accountant_id')
        tax_year = client_info.get('tax_year', datetime.now().year)
        
        template = get_default_template(followup_number)
        personalized = personalize_email(template, client_info, missing_documents, tax_year)
        
        if custom_message:
            personalized['body'] = f"{custom_message}\n\n{personalized['body']}"
        
        message_id = send_email_via_ses(
            to_email=client_info['email'],
            subject=personalized['subject'],
            body=personalized['body']
        )
        
        # Track usage for billing
        track_usage(
            accountant_id=accountant_id,
            operation='send_reminder_email',
            resource_type='email_sent',
            quantity=1,
            metadata={'client_id': client_id, 'followup_number': followup_number}
        )
        
        followup_id = log_followup(
            client_id=client_id,
            followup_number=followup_number,
            email_subject=personalized['subject'],
            email_body=personalized['body'],
            missing_docs=missing_documents,
            accountant_id=accountant_id
        )
        
        next_followup = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        response = {
            'success': True,
            'email_sent': True,
            'recipient': client_info['email'],
            'subject': personalized['subject'],
            'sent_at': datetime.utcnow().isoformat(),
            'followup_id': followup_id,
            'followup_number': followup_number,
            'next_followup_date': next_followup,
            'message_id': message_id
        }
        
        logger.info(f"Email sent successfully to {client_info['email']}")
        
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps(response, indent=2)
            }]
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps({
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            }]
        }
