# Remaining Gateway Tools - Complete Implementation

## Tool 4: Escalation Manager Lambda

**Purpose:** Mark clients for accountant intervention and send notifications

**File:** `gateway/tools/escalation_manager/escalation_manager_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')
sns = boto3.client('sns')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SETTINGS_TABLE = os.environ['SETTINGS_TABLE']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']
ESCALATION_SNS_TOPIC = os.environ.get('ESCALATION_SNS_TOPIC')


def get_client_info(client_id: str) -> Dict[str, Any]:
    """
    Get client information from DynamoDB.
    
    Args:
        client_id: Unique client identifier
    
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


def get_accountant_info(accountant_id: str) -> Dict[str, Any]:
    """
    Get accountant contact information.
    
    Args:
        accountant_id: Accountant identifier
    
    Returns:
        Accountant information dictionary
    """
    table = dynamodb.Table(SETTINGS_TABLE)
    
    try:
        response = table.get_item(
            Key={
                'accountant_id': accountant_id,
                'settings_type': 'contact_info'
            }
        )
        
        if 'Item' in response:
            return response['Item']
        
        # Return minimal defaults
        return {
            'accountant_id': accountant_id,
            'email': None,
            'phone': None,
            'name': 'Accountant'
        }
        
    except ClientError as e:
        logger.error(f"Error getting accountant info: {e}")
        return {
            'accountant_id': accountant_id,
            'email': None,
            'phone': None,
            'name': 'Accountant'
        }


def update_client_status(client_id: str, status: str) -> None:
    """
    Update client status to escalated.
    
    Args:
        client_id: Client identifier
        status: New status (should be 'escalated')
    
    Raises:
        ClientError: If DynamoDB update fails
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    try:
        table.update_item(
            Key={'client_id': client_id},
            UpdateExpression='SET #status = :status, escalated_at = :escalated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': status,
                ':escalated_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Updated client {client_id} status to {status}")
        
    except ClientError as e:
        logger.error(f"Error updating client status: {e}")
        raise


def log_escalation(
    client_id: str,
    reason: str,
    accountant_id: str,
    notification_sent: bool
) -> str:
    """
    Log escalation event to follow-up history.
    
    Args:
        client_id: Client identifier
        reason: Reason for escalation
        accountant_id: Accountant identifier
        notification_sent: Whether notification was sent
    
    Returns:
        Escalation event ID
    
    Raises:
        ClientError: If DynamoDB write fails
    """
    table = dynamodb.Table(FOLLOWUP_TABLE)
    
    escalation_id = f"esc_{int(datetime.utcnow().timestamp())}"
    
    try:
        table.put_item(
            Item={
                'client_id': client_id,
                'followup_id': escalation_id,
                'event_type': 'escalation',
                'escalated_at': datetime.utcnow().isoformat(),
                'reason': reason,
                'accountant_id': accountant_id,
                'notification_sent': notification_sent,
                'escalation_triggered': True
            }
        )
        
        logger.info(f"Logged escalation: {escalation_id}")
        return escalation_id
        
    except ClientError as e:
        logger.error(f"Error logging escalation: {e}")
        raise


def send_email_notification(
    accountant_email: str,
    client_info: Dict[str, Any],
    reason: str
) -> Optional[str]:
    """
    Send email notification to accountant.
    
    Args:
        accountant_email: Accountant's email address
        client_info: Client information dictionary
        reason: Escalation reason
    
    Returns:
        SES message ID if successful, None otherwise
    """
    if not accountant_email:
        logger.warning("No accountant email provided, skipping email notification")
        return None
    
    client_name = client_info.get('client_name', 'Unknown Client')
    client_email = client_info.get('email', 'N/A')
    client_phone = client_info.get('phone', 'N/A')
    
    subject = f"ESCALATION: Client {client_name} requires immediate attention"
    
    body = f"""ESCALATION ALERT

Client: {client_name}
Email: {client_email}
Phone: {client_phone}

Reason for Escalation:
{reason}

Action Required:
Please contact this client directly to resolve the outstanding document collection issue.

This is an automated notification from the Tax Document Collection System.
"""
    
    try:
        response = ses.send_email(
            Source=SES_FROM_EMAIL,
            Destination={'ToAddresses': [accountant_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}
            }
        )
        
        message_id = response['MessageId']
        logger.info(f"Email notification sent: {message_id}")
        
        return message_id
        
    except ClientError as e:
        logger.error(f"Error sending email notification: {e}")
        return None


def send_sns_notification(
    client_info: Dict[str, Any],
    reason: str
) -> Optional[str]:
    """
    Send SNS notification for escalation.
    
    Args:
        client_info: Client information dictionary
        reason: Escalation reason
    
    Returns:
        SNS message ID if successful, None otherwise
    """
    if not ESCALATION_SNS_TOPIC:
        logger.info("No SNS topic configured, skipping SNS notification")
        return None
    
    client_name = client_info.get('client_name', 'Unknown Client')
    
    message = {
        'event_type': 'client_escalation',
        'client_id': client_info['client_id'],
        'client_name': client_name,
        'reason': reason,
        'escalated_at': datetime.utcnow().isoformat()
    }
    
    try:
        response = sns.publish(
            TopicArn=ESCALATION_SNS_TOPIC,
            Message=json.dumps(message),
            Subject=f"Client Escalation: {client_name}",
            MessageAttributes={
                'event_type': {
                    'DataType': 'String',
                    'StringValue': 'client_escalation'
                }
            }
        )
        
        message_id = response['MessageId']
        logger.info(f"SNS notification sent: {message_id}")
        
        return message_id
        
    except ClientError as e:
        logger.error(f"Error sending SNS notification: {e}")
        return None


def get_escalation_reason_details(
    client_id: str,
    custom_reason: Optional[str] = None
) -> str:
    """
    Build detailed escalation reason.
    
    Args:
        client_id: Client identifier
        custom_reason: Optional custom reason provided
    
    Returns:
        Detailed escalation reason string
    """
    if custom_reason:
        return custom_reason
    
    # Get follow-up history to build automatic reason
    table = dynamodb.Table(FOLLOWUP_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='client_id = :cid',
            ExpressionAttributeValues={':cid': client_id},
            ScanIndexForward=False,  # Most recent first
            Limit=5
        )
        
        followups = response.get('Items', [])
        
        if not followups:
            return "Client has not responded to document requests"
        
        followup_count = len(followups)
        last_followup = followups[0]
        last_date = last_followup.get('sent_date', 'Unknown')
        
        # Calculate days since last contact
        if last_date != 'Unknown':
            last_datetime = datetime.fromisoformat(last_date)
            days_since = (datetime.utcnow() - last_datetime).days
        else:
            days_since = 0
        
        reason = f"No response after {followup_count} reminders over {days_since} days. "
        reason += f"Last contact: {last_date[:10]}. "
        reason += "Client requires direct phone call or in-person follow-up."
        
        return reason
        
    except ClientError as e:
        logger.error(f"Error building escalation reason: {e}")
        return "Client requires immediate attention for document collection"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for escalating clients.
    
    Args:
        event: Lambda event containing escalation parameters
        context: Lambda context object
    
    Returns:
        Dictionary with escalation confirmation
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
        custom_reason = event.get('reason')
        notify_accountant = event.get('notify_accountant', True)
        
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        # Get client information
        client_info = get_client_info(client_id)
        accountant_id = client_info.get('accountant_id')
        
        if not accountant_id:
            raise ValueError(f"Client {client_id} has no associated accountant")
        
        # Build escalation reason
        escalation_reason = get_escalation_reason_details(client_id, custom_reason)
        
        # Update client status
        update_client_status(client_id, 'escalated')
        
        # Send notifications if requested
        notification_sent = False
        email_message_id = None
        sns_message_id = None
        
        if notify_accountant:
            # Get accountant info
            accountant_info = get_accountant_info(accountant_id)
            
            # Send email notification
            if accountant_info.get('email'):
                email_message_id = send_email_notification(
                    accountant_email=accountant_info['email'],
                    client_info=client_info,
                    reason=escalation_reason
                )
                notification_sent = email_message_id is not None
            
            # Send SNS notification
            sns_message_id = send_sns_notification(
                client_info=client_info,
                reason=escalation_reason
            )
        
        # Log escalation event
        escalation_id = log_escalation(
            client_id=client_id,
            reason=escalation_reason,
            accountant_id=accountant_id,
            notification_sent=notification_sent
        )
        
        # Build response
        response = {
            'success': True,
            'client_id': client_id,
            'client_name': client_info.get('client_name', 'Unknown'),
            'escalated_at': datetime.utcnow().isoformat(),
            'escalation_id': escalation_id,
            'escalation_reason': escalation_reason,
            'accountant_notified': notification_sent,
            'email_message_id': email_message_id,
            'sns_message_id': sns_message_id,
            'next_action': 'Accountant should contact client directly via phone or in-person'
        }
        
        logger.info(f"Client {client_id} escalated successfully")
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(response, indent=2)
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }
            ]
        }
```

**Tool Spec:** `gateway/tools/escalation_manager/tool_spec.json`

```json
{
  "name": "escalate_client",
  "description": "Mark client for accountant intervention and send notifications. Use when client has not responded after multiple reminders and requires direct contact.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "client_id": {
        "type": "string",
        "description": "Unique client identifier to escalate"
      },
      "reason": {
        "type": "string",
        "description": "Reason for escalation. If not provided, system will generate reason based on follow-up history."
      },
      "notify_accountant": {
        "type": "boolean",
        "description": "Whether to send notification to accountant (default: true)"
      }
    },
    "required": ["client_id"]
  }
}
```

