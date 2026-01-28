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
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']
SMS_SENDER_ID = os.environ.get('SMS_SENDER_ID', 'YourFirm')
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
        
        pricing = {'email_sent': 0.0001, 'sms_sent': 0.00645}
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


def send_sms_via_sns(
    phone_number: str,
    message: str
) -> Optional[str]:
    """
    Send SMS via AWS SNS.
    
    Args:
        phone_number: E.164 format phone number (+12065551234)
        message: SMS text content (max 160 chars)
    
    Returns:
        SNS message ID if successful, None if failed
    """
    try:
        # Validate phone number format
        import re
        if not re.match(r'^\+1[2-9]\d{9}$', phone_number):
            logger.error(f"Invalid phone number format: {phone_number}")
            return None
        
        # Check if within allowed sending hours (8 AM - 8 PM)
        current_hour = datetime.utcnow().hour
        # Allow 13:00 UTC - 03:59 UTC (covers all US timezones 8 AM - 8 PM)
        if not (13 <= current_hour or current_hour < 4):
            logger.warning(f"Outside allowed SMS hours. Current UTC hour: {current_hour}")
            return None
        
        # Truncate message if too long
        if len(message) > 160:
            message = message[:157] + '...'
        
        # Send SMS
        response = sns.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                },
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': SMS_SENDER_ID[:11]
                }
            }
        )
        message_id = response['MessageId']
        logger.info(f"SMS sent successfully: {message_id} to {phone_number}")
        return message_id
    except ClientError as e:
        logger.error(f"Error sending SMS via SNS: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending SMS: {e}")
        return None


def create_sms_message(
    client_name: str,
    upload_url: str,
    days_valid: int
) -> str:
    """
    Create concise SMS message for upload link.
    
    Args:
        client_name: Client's name
        upload_url: Upload portal URL
        days_valid: Number of days link is valid
    
    Returns:
        Formatted SMS message (max 160 chars)
    """
    # Use first name only to save characters
    first_name = client_name.split()[0] if client_name else 'there'
    
    message = f"Hi {first_name}, upload your tax docs: {upload_url} (valid {days_valid}d). Reply STOP to opt out."
    
    # Ensure within 160 char limit
    if len(message) > 160:
        message = message[:157] + '...'
    
    return message


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
        send_via = event.get('send_via', 'both')  # 'email', 'sms', or 'both'
        
        # Validate required parameters
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        # Validate days_valid range
        if not (1 <= days_valid <= 90):
            raise ValueError("days_valid must be between 1 and 90")
        
        # Get client information
        client_info = get_client_info(client_id)
        client_email = client_info.get('email')
        client_phone = client_info.get('phone')
        sms_enabled = client_info.get('sms_enabled', False)
        accountant_id = client_info.get('accountant_id', 'unknown')
        
        if not client_email and not (client_phone and sms_enabled):
            raise ValueError(f"Client {client_id} has no email or SMS contact information")
        
        # Generate upload token
        upload_token, token_expires = generate_upload_token(
            client_id=client_id, 
            days_valid=days_valid,
            reminder_preferences=reminder_preferences
        )
        
        # Generate upload URL
        upload_url = generate_upload_url(client_id, upload_token)
        
        # Track what was sent
        sent_channels = []
        message_ids = {}
        
        # Send email if requested and available
        if send_via in ['email', 'both'] and client_email:
            try:
                email_subject = f"Secure Link to Upload Your {client_info.get('tax_year', datetime.now().year)} Tax Documents"
                email_body = create_email_body(client_info, upload_url, days_valid, custom_message)
                email_id = send_email_via_ses(
                    to_email=client_email,
                    subject=email_subject,
                    body=email_body
                )
                message_ids['email'] = email_id
                sent_channels.append('email')
                
                # Track email usage
                track_usage(
                    accountant_id=accountant_id,
                    operation='send_upload_link',
                    resource_type='email_sent',
                    quantity=1
                )
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
        
        # Send SMS if requested, enabled, and available
        if send_via in ['sms', 'both'] and client_phone and sms_enabled:
            try:
                sms_message = create_sms_message(
                    client_name=client_info.get('client_name', 'Client'),
                    upload_url=upload_url,
                    days_valid=days_valid
                )
                sms_id = send_sms_via_sns(client_phone, sms_message)
                if sms_id:
                    message_ids['sms'] = sms_id
                    sent_channels.append('sms')
                    
                    # Track SMS usage
                    track_usage(
                        accountant_id=accountant_id,
                        operation='send_upload_link',
                        resource_type='sms_sent',
                        quantity=1
                    )
            except Exception as e:
                logger.error(f"Failed to send SMS: {e}")
        
        if not sent_channels:
            raise ValueError("Failed to send notification via any channel")
        
        # Log to DynamoDB
        log_id = log_upload_link_sent(
            client_id=client_id,
            upload_token=upload_token,
            token_expires=token_expires,
            message_id=message_ids.get('email', 'N/A'),
            recipient_email=client_email or 'N/A',
            accountant_id=accountant_id
        )
        
        # Prepare response
        response = {
            'success': True,
            'upload_link_sent': True,
            'client_id': client_id,
            'client_name': client_info.get('client_name'),
            'channels': sent_channels,
            'recipient_email': client_email if 'email' in sent_channels else None,
            'recipient_phone': client_phone if 'sms' in sent_channels else None,
            'upload_url': upload_url,
            'token_expires': token_expires[:10],  # Just the date
            'days_valid': days_valid,
            'sent_at': datetime.utcnow().isoformat(),
            'message_ids': message_ids,
            'log_id': log_id
        }
        
        logger.info(f"Upload link sent successfully via {', '.join(sent_channels)}")
        
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

