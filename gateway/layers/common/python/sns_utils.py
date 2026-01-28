# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
SNS Utilities for SMS Notifications

Provides helper functions for sending SMS messages via Amazon SNS
with proper validation, timing checks, and error handling.
"""

import boto3
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger()
sns = boto3.client('sns')

# US phone number regex (E.164 format: +1XXXXXXXXXX)
PHONE_REGEX = re.compile(r'^\+1[2-9]\d{9}$')

# SMS character limits
SMS_SINGLE_LIMIT = 160
SMS_MULTI_SEGMENT = 153


def validate_phone_number(phone: str) -> bool:
    """
    Validate US phone number in E.164 format.
    
    Args:
        phone: Phone number string
    
    Returns:
        True if valid, False otherwise
    
    Examples:
        Valid: +12065551234
        Invalid: 2065551234, +1206555123, +442071234567
    """
    if not phone:
        return False
    return bool(PHONE_REGEX.match(phone))


def is_valid_send_time(hour: int = None) -> bool:
    """
    Check if current time is within allowed sending window (8 AM - 8 PM).
    
    Args:
        hour: Optional hour to check (0-23). If None, uses current UTC hour.
    
    Returns:
        True if within allowed window, False otherwise
    
    Note:
        This uses UTC time. For production, should convert to client's timezone.
        Current implementation assumes US timezones (UTC-5 to UTC-8).
    """
    if hour is None:
        hour = datetime.utcnow().hour
    
    # Convert UTC to US timezones (rough approximation)
    # EST: UTC-5, CST: UTC-6, MST: UTC-7, PST: UTC-8
    # Allow sending if ANY US timezone is between 8 AM - 8 PM
    # This means UTC hours: 13:00 - 04:00 (next day)
    
    # For simplicity, allow 13:00 UTC - 03:59 UTC (covers all US timezones)
    return 13 <= hour or hour < 4


def truncate_message(message: str, max_length: int = SMS_SINGLE_LIMIT) -> str:
    """
    Truncate message to fit SMS length limits.
    
    Args:
        message: Original message
        max_length: Maximum length (default: 160 for single SMS)
    
    Returns:
        Truncated message with ellipsis if needed
    """
    if len(message) <= max_length:
        return message
    
    # Reserve 3 chars for ellipsis
    return message[:max_length - 3] + '...'


def send_sms(
    phone_number: str,
    message: str,
    sender_id: str = 'YourFirm',
    check_time: bool = True
) -> Dict[str, Any]:
    """
    Send SMS via Amazon SNS with validation and error handling.
    
    Args:
        phone_number: E.164 format phone number (+12065551234)
        message: SMS text content
        sender_id: Sender ID to display (max 11 chars)
        check_time: Whether to check if within allowed sending hours
    
    Returns:
        Dictionary with:
            - success: bool
            - message_id: str (if successful)
            - error: str (if failed)
            - segments: int (number of SMS segments)
    
    Raises:
        ValueError: If phone number is invalid
        ClientError: If SNS publish fails
    """
    # Validate phone number
    if not validate_phone_number(phone_number):
        raise ValueError(f"Invalid US phone number format: {phone_number}. Must be E.164 format (+1XXXXXXXXXX)")
    
    # Check sending time
    if check_time and not is_valid_send_time():
        current_hour = datetime.utcnow().hour
        return {
            'success': False,
            'error': f'Outside allowed sending hours (8 AM - 8 PM). Current UTC hour: {current_hour}',
            'skipped': True
        }
    
    # Truncate message if too long
    original_length = len(message)
    message = truncate_message(message, SMS_SINGLE_LIMIT)
    
    if len(message) < original_length:
        logger.warning(f"Message truncated from {original_length} to {len(message)} characters")
    
    # Calculate segments
    segments = 1 if len(message) <= SMS_SINGLE_LIMIT else (len(message) // SMS_MULTI_SEGMENT) + 1
    
    try:
        # Prepare SNS publish parameters
        params = {
            'PhoneNumber': phone_number,
            'Message': message,
            'MessageAttributes': {
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'  # Higher priority, better delivery
                }
            }
        }
        
        # Add sender ID if provided (max 11 chars)
        if sender_id:
            params['MessageAttributes']['AWS.SNS.SMS.SenderID'] = {
                'DataType': 'String',
                'StringValue': sender_id[:11]
            }
        
        # Send SMS via SNS
        response = sns.publish(**params)
        message_id = response['MessageId']
        
        logger.info(f"SMS sent successfully to {phone_number}: {message_id} ({segments} segment(s))")
        
        return {
            'success': True,
            'message_id': message_id,
            'segments': segments,
            'phone_number': phone_number
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"SNS publish failed: {error_code} - {error_message}")
        
        return {
            'success': False,
            'error': f"{error_code}: {error_message}",
            'phone_number': phone_number
        }
    except Exception as e:
        logger.error(f"Unexpected error sending SMS: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number
        }


def create_upload_link_sms(
    client_name: str,
    upload_url: str,
    days_valid: int
) -> str:
    """
    Create SMS message for upload link notification.
    
    Args:
        client_name: Client's first name
        upload_url: Upload portal URL
        days_valid: Number of days link is valid
    
    Returns:
        Formatted SMS message (max 160 chars)
    
    Example:
        "Hi John, upload your tax docs: https://short.url/abc (valid 30d). Reply STOP to opt out."
    """
    # Use first name only to save characters
    first_name = client_name.split()[0] if client_name else 'there'
    
    # Create concise message
    message = f"Hi {first_name}, upload your tax docs: {upload_url} (valid {days_valid}d). Reply STOP to opt out."
    
    return truncate_message(message, SMS_SINGLE_LIMIT)


def create_reminder_sms(
    client_name: str,
    missing_docs: list,
    upload_url: str
) -> str:
    """
    Create SMS message for document reminder.
    
    Args:
        client_name: Client's first name
        missing_docs: List of missing document types
        upload_url: Upload portal URL
    
    Returns:
        Formatted SMS message (max 160 chars)
    
    Example:
        "Reminder: We need your W-2, 1099-INT for 2026 taxes. Upload: https://short.url/abc Reply STOP to opt out."
    """
    first_name = client_name.split()[0] if client_name else 'there'
    
    # Limit to first 2 documents to save space
    docs_str = ', '.join(missing_docs[:2])
    if len(missing_docs) > 2:
        docs_str += f' +{len(missing_docs) - 2} more'
    
    message = f"Reminder: We need your {docs_str} for 2026 taxes. Upload: {upload_url} Reply STOP to opt out."
    
    return truncate_message(message, SMS_SINGLE_LIMIT)


def create_status_update_sms(
    client_name: str,
    doc_type: str,
    remaining: int
) -> str:
    """
    Create SMS message for status update.
    
    Args:
        client_name: Client's first name
        doc_type: Document type received
        remaining: Number of documents still needed
    
    Returns:
        Formatted SMS message (max 160 chars)
    
    Example:
        "Great! We received your W-2. 3 documents remaining. Reply STOP to opt out."
    """
    first_name = client_name.split()[0] if client_name else 'there'
    
    if remaining == 0:
        message = f"Great {first_name}! We received your {doc_type}. All documents complete! Reply STOP to opt out."
    else:
        message = f"Great! We received your {doc_type}. {remaining} document(s) remaining. Reply STOP to opt out."
    
    return truncate_message(message, SMS_SINGLE_LIMIT)


def set_sns_spending_limit(limit_usd: float = 10.0) -> bool:
    """
    Set monthly SMS spending limit in SNS.
    
    Args:
        limit_usd: Monthly spending limit in USD
    
    Returns:
        True if successful, False otherwise
    
    Note:
        This sets the account-level spending limit for SMS.
        Requires SNS:SetSMSAttributes permission.
    """
    try:
        sns.set_sms_attributes(
            attributes={
                'MonthlySpendLimit': str(limit_usd)
            }
        )
        logger.info(f"SNS monthly spending limit set to ${limit_usd}")
        return True
    except ClientError as e:
        logger.error(f"Failed to set SNS spending limit: {e}")
        return False


def get_sns_spending_info() -> Dict[str, Any]:
    """
    Get current SNS SMS spending information.
    
    Returns:
        Dictionary with spending limit and current spend
    """
    try:
        response = sns.get_sms_attributes(
            attributes=['MonthlySpendLimit']
        )
        return {
            'monthly_limit': response.get('attributes', {}).get('MonthlySpendLimit', 'Not set'),
            'success': True
        }
    except ClientError as e:
        logger.error(f"Failed to get SNS spending info: {e}")
        return {
            'success': False,
            'error': str(e)
        }
