# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Send Upload Link Lambda - Generate secure upload token and send email with upload portal link.

This Lambda combines token generation and email sending to provide a fully automated
way for accountants to send upload links to clients via the AI agent.
"""

import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses = boto3.client('ses')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://yourdomain.com')
USAGE_TABLE = os.environ.get('USAGE_TABLE', '')


def track_usage(accountant_id: str, operation: str, resource_type: str, quantity: float = 1.0):
    """Track usage for billing."""
    if not USAGE_TABLE:
        return
    
    try:
        from datetime import datetime
        from decimal import Decimal
        
        usage_table = dynamodb.Table(USAGE_TABLE)
        timestamp = datetime.utcnow().isoformat()
        month = timestamp[:7]
        
        pricing = {'email_sent': 0.0001}
        unit_cost = pricing.get(resource_type, 0.0)
        estimated_cost = unit_cost * quantity
        
        usage_table.put_item(Item={
            'accountant_id': accountant_id,
            'timestamp': timestamp,
            'month': month,
            'operation': operation,
            'resource_type': resource_type,
            'quantity': Decimal(str(quantity)),
            'unit_cost': Decimal(str(unit_cost)),
            'estimated_cost': Decimal(str(estimated_cost))
        })
        
        logger.info(f"Tracked usage: {operation}, cost: ${estimated_cost:.6f}")
    except Exception as e:
        logger.error(f"Error tracking usage: {e}")


def get_client_info(client_id: str) -> Dict[str, Any]:
    """
    Get client information from DynamoDB.
    
    Args:
        client_id: Client identifier
    
    Returns:
        Client information dictionary
    
    Raises:
        ValueError: If client not found
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    try:
        response = table.get_item(Key={'client_id': client_id})
        if 'Item' not in response:
            raise ValueError(f"Client not found: {client_id}")
        return response['Item']
    except ClientError as e:
        logger.error(f"Error getting client info: {e}")
        raise


def generate_upload_token(client_id: str, days_valid: int = 30, reminder_preferences: Optional[Dict[str, int]] = None) -> tuple[str, str]:
    """
    Generate secure upload token and update client record.
    
    Args:
        client_id: Client identifier
        days_valid: Number of days token is valid
        reminder_preferences: Optional reminder timing preferences
    
    Returns:
        Tuple of (upload_token, token_expires)
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    # Generate secure random token (32 bytes = 43 characters base64)
    upload_token = secrets.token_urlsafe(32)
    token_expires = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    
    try:
        # Build update expression
        update_expression = 'SET upload_token = :token, token_expires = :expires, token_generated_at = :generated'
        expression_values = {
            ':token': upload_token,
            ':expires': token_expires,
            ':generated': datetime.utcnow().isoformat()
        }
        
        # Add reminder preferences if provided
        if reminder_preferences:
            update_expression += ', reminder_preferences = :prefs'
            expression_values[':prefs'] = reminder_preferences
        
        # Update client record with token
        table.update_item(
            Key={'client_id': client_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        logger.info(f"Upload token generated for client {client_id}, expires: {token_expires}")
        return upload_token, token_expires
        
    except ClientError as e:
        logger.error(f"Error updating client with token: {e}")
        raise


def generate_upload_url(client_id: str, upload_token: str) -> str:
    """
    Generate upload portal URL with client ID and token.
    
    Args:
        client_id: Client identifier
        upload_token: Secure upload token
    
    Returns:
        Complete upload portal URL
    """
    # Construct URL with query parameters (no trailing slash)
    upload_url = f"{FRONTEND_URL}/upload?client={client_id}&token={upload_token}"
    return upload_url


def create_email_body(
    client_info: Dict[str, Any],
    upload_url: str,
    days_valid: int,
    custom_message: Optional[str] = None
) -> str:
    """
    Create personalized email body for upload link.
    
    Args:
        client_info: Client information dictionary
        upload_url: Upload portal URL
        days_valid: Number of days link is valid
        custom_message: Optional custom message from accountant
    
    Returns:
        Formatted email body
    """
    client_name = client_info.get('client_name', 'Valued Client')
    accountant_name = client_info.get('accountant_name', 'Your Accountant')
    accountant_firm = client_info.get('accountant_firm', '')
    accountant_phone = client_info.get('accountant_phone', '')
    tax_year = client_info.get('tax_year', datetime.now().year)
    
    # Build email body
    email_body = f"""Dear {client_name},

I hope this email finds you well. I'm reaching out regarding your {tax_year} tax return.

Please upload your tax documents using this secure link:

{upload_url}

This link is valid for {days_valid} days and is unique to you. No login is required.

"""
    
    # Add custom message if provided
    if custom_message:
        email_body += f"{custom_message}\n\n"
    
    # Add standard instructions
    email_body += """Required documents may include:
- W-2 forms from all employers
- 1099 forms from all sources (INT, DIV, MISC, NEC, B, R)
- Prior year tax return
- Receipts for deductions
- Any other relevant tax documents

Instructions:
1. Click the link above
2. Select the document type
3. Choose your PDF file (max 10 MB)
4. Click "Upload Document"
5. Repeat for each document

Your documents are encrypted and securely stored. Only I can access them.

"""
    
    # Add contact information
    email_body += f"""If you have any questions or need assistance, please don't hesitate to contact me.

Best regards,
{accountant_name}"""
    
    if accountant_firm:
        email_body += f"\n{accountant_firm}"
    
    if accountant_phone:
        email_body += f"\nPhone: {accountant_phone}"
    
    return email_body


def send_email_via_ses(
    to_email: str,
    subject: str,
    body: str
) -> str:
    """
    Send email via AWS SES.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body
    
    Returns:
        SES message ID
    
    Raises:
        ClientError: If email sending fails
    """
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
        logger.info(f"Email sent successfully: {message_id} to {to_email}")
        return message_id
    except ClientError as e:
        logger.error(f"Error sending email via SES: {e}")
        raise


def log_upload_link_sent(
    client_id: str,
    upload_token: str,
    token_expires: str,
    message_id: str,
    recipient_email: str,
    accountant_id: str
) -> str:
    """
    Log upload link sending to DynamoDB for audit trail.
    
    Args:
        client_id: Client identifier
        upload_token: Generated token
        token_expires: Token expiration date
        message_id: SES message ID
        recipient_email: Client email
        accountant_id: Accountant identifier
    
    Returns:
        Log entry ID
    """
    table = dynamodb.Table(FOLLOWUP_TABLE)
    log_id = f"upload_link_{int(datetime.utcnow().timestamp())}"
    sent_date = datetime.utcnow().isoformat()
    
    try:
        table.put_item(
            Item={
                'client_id': client_id,
                'followup_id': log_id,
                'followup_type': 'upload_link',
                'sent_date': sent_date,
                'email_subject': 'Secure Link to Upload Your Tax Documents',
                'recipient_email': recipient_email,
                'upload_token': upload_token,
                'token_expires': token_expires,
                'ses_message_id': message_id,
                'link_used': False,
                'accountant_id': accountant_id
            }
        )
        logger.info(f"Upload link logged: {log_id}")
        return log_id
    except ClientError as e:
        logger.error(f"Error logging upload link: {e}")
        # Don't raise - logging failure shouldn't fail the operation
        return "log_failed"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for sending upload links.
    
    Args:
        event: Gateway event with client_id, days_valid, custom_message
        context: Lambda context
    
    Returns:
        Response with success status and upload URL
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
        days_valid = event.get('days_valid', 30)
        custom_message = event.get('custom_message')
        reminder_preferences = event.get('reminder_preferences')
        
        # Validate required parameters
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        # Validate days_valid range
        if not (1 <= days_valid <= 90):
            raise ValueError("days_valid must be between 1 and 90")
        
        # Get client information
        client_info = get_client_info(client_id)
        client_email = client_info.get('email')
        accountant_id = client_info.get('accountant_id', 'unknown')
        
        if not client_email:
            raise ValueError(f"Client {client_id} has no email address on file")
        
        # Generate upload token
        upload_token, token_expires = generate_upload_token(
            client_id=client_id, 
            days_valid=days_valid,
            reminder_preferences=reminder_preferences
        )
        
        # Generate upload URL
        upload_url = generate_upload_url(client_id, upload_token)
        
        # Create email body
        email_subject = f"Secure Link to Upload Your {client_info.get('tax_year', datetime.now().year)} Tax Documents"
        email_body = create_email_body(client_info, upload_url, days_valid, custom_message)
        
        # Send email via SES
        message_id = send_email_via_ses(
            to_email=client_email,
            subject=email_subject,
            body=email_body
        )
        
        # Log to DynamoDB
        log_id = log_upload_link_sent(
            client_id=client_id,
            upload_token=upload_token,
            token_expires=token_expires,
            message_id=message_id,
            recipient_email=client_email,
            accountant_id=accountant_id
        )
        
        # Track usage for billing
        track_usage(
            accountant_id=accountant_id,
            operation='send_upload_link',
            resource_type='email_sent',
            quantity=1
        )
        
        # Prepare response
        response = {
            'success': True,
            'upload_link_sent': True,
            'client_id': client_id,
            'client_name': client_info.get('client_name'),
            'recipient': client_email,
            'upload_url': upload_url,
            'token_expires': token_expires[:10],  # Just the date
            'days_valid': days_valid,
            'sent_at': datetime.utcnow().isoformat(),
            'message_id': message_id,
            'log_id': log_id
        }
        
        logger.info(f"Upload link sent successfully to {client_email}")
        
        # Return in Gateway format
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps(response, indent=2)
            }]
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps({
                    'success': False,
                    'error': str(e),
                    'error_type': 'ValidationError'
                })
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

