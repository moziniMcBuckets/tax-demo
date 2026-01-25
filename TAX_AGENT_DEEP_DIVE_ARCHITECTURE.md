# Tax Document Agent - Deep Dive Architecture

## Complete Implementation Guide

This document provides complete, production-ready code for all components of the tax document collection agent.

---

## Part 1: Gateway Lambda Tools

### Tool 1: Document Checker Lambda

**Purpose:** Scan S3 client folders and identify missing documents

**File:** `gateway/tools/document_checker/document_checker_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
CLIENT_BUCKET = os.environ['CLIENT_BUCKET']

# Document type patterns for classification
DOCUMENT_PATTERNS = {
    'W-2': ['w2', 'w-2', 'wage', 'tax statement'],
    '1099-INT': ['1099-int', '1099int', 'interest income'],
    '1099-DIV': ['1099-div', '1099div', 'dividend'],
    '1099-MISC': ['1099-misc', '1099misc', 'miscellaneous'],
    '1099-NEC': ['1099-nec', '1099nec', 'non-employee'],
    '1099-B': ['1099-b', '1099b', 'broker'],
    '1099-R': ['1099-r', '1099r', 'retirement'],
}


def classify_document(filename: str, metadata: Dict[str, str]) -> str:
    """
    Classify document type based on filename and S3 metadata.
    
    Args:
        filename: Name of the file
        metadata: S3 object metadata
    
    Returns:
        Document type string (e.g., 'W-2', '1099-INT', 'Unknown')
    """
    filename_lower = filename.lower()
    
    # Check metadata first (most reliable)
    if 'document-type' in metadata:
        return metadata['document-type']
    
    # Pattern matching on filename
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        if any(pattern in filename_lower for pattern in patterns):
            return doc_type
    
    return 'Unknown'


def scan_client_folder(client_id: str, tax_year: int) -> List[Dict[str, Any]]:
    """
    Scan S3 folder for client documents.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year to scan
    
    Returns:
        List of document dictionaries with metadata
    """
    prefix = f"{client_id}/{tax_year}/"
    documents = []
    
    try:
        # List objects in client folder
        response = s3.list_objects_v2(
            Bucket=CLIENT_BUCKET,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.info(f"No documents found for client {client_id}, year {tax_year}")
            return documents
        
        # Process each document
        for obj in response['Contents']:
            key = obj['Key']
            
            # Skip folder markers
            if key.endswith('/'):
                continue
            
            # Get object metadata (no data transfer cost!)
            head_response = s3.head_object(Bucket=CLIENT_BUCKET, Key=key)
            metadata = head_response.get('Metadata', {})
            
            filename = key.split('/')[-1]
            doc_type = classify_document(filename, metadata)
            
            documents.append({
                'filename': filename,
                'document_type': doc_type,
                'upload_date': obj['LastModified'].isoformat(),
                'size_bytes': obj['Size'],
                's3_key': key,
            })
        
        logger.info(f"Found {len(documents)} documents for client {client_id}")
        return documents
        
    except ClientError as e:
        logger.error(f"Error scanning S3 folder: {e}")
        raise


def get_required_documents(client_id: str, tax_year: int) -> List[Dict[str, Any]]:
    """
    Get list of required documents from DynamoDB.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year
    
    Returns:
        List of required document dictionaries
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression='client_id = :cid',
            ExpressionAttributeValues={':cid': client_id}
        )
        
        required_docs = [
            item for item in response['Items']
            if item.get('required', False) and item.get('tax_year') == tax_year
        ]
        
        return required_docs
        
    except ClientError as e:
        logger.error(f"Error querying DynamoDB: {e}")
        raise


def update_document_status(
    client_id: str,
    tax_year: int,
    received_documents: List[Dict[str, Any]]
) -> None:
    """
    Update document receipt status in DynamoDB.
    
    Args:
        client_id: Unique client identifier
        tax_year: Tax year
        received_documents: List of received documents
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    # Create a map of received document types
    received_types = {doc['document_type'] for doc in received_documents}
    
    try:
        # Get all required documents
        required_docs = get_required_documents(client_id, tax_year)
        
        # Update each document's status
        for doc in required_docs:
            doc_type = doc['document_type']
            received = doc_type in received_types
            
            table.update_item(
                Key={
                    'client_id': client_id,
                    'document_type': doc_type
                },
                UpdateExpression='SET received = :r, last_checked = :lc',
                ExpressionAttributeValues={
                    ':r': received,
                    ':lc': datetime.utcnow().isoformat()
                }
            )
        
        logger.info(f"Updated document status for client {client_id}")
        
    except ClientError as e:
        logger.error(f"Error updating DynamoDB: {e}")
        raise


def calculate_completion_percentage(
    required_docs: List[Dict[str, Any]],
    received_docs: List[Dict[str, Any]]
) -> int:
    """
    Calculate completion percentage.
    
    Args:
        required_docs: List of required documents
        received_docs: List of received documents
    
    Returns:
        Completion percentage (0-100)
    """
    if not required_docs:
        return 100
    
    received_types = {doc['document_type'] for doc in received_docs}
    required_types = {doc['document_type'] for doc in required_docs}
    
    matched = len(received_types & required_types)
    total = len(required_types)
    
    return int((matched / total) * 100)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document checking.
    
    Args:
        event: Lambda event containing client_id and tax_year
        context: Lambda context object
    
    Returns:
        Dictionary with document status information
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
        tax_year = event.get('tax_year')
        
        if not client_id or not tax_year:
            raise ValueError("Missing required parameters: client_id, tax_year")
        
        # Scan client folder
        received_documents = scan_client_folder(client_id, tax_year)
        
        # Get required documents
        required_documents = get_required_documents(client_id, tax_year)
        
        # Update status in DynamoDB
        update_document_status(client_id, tax_year, received_documents)
        
        # Calculate completion
        completion_pct = calculate_completion_percentage(
            required_documents,
            received_documents
        )
        
        # Identify missing documents
        received_types = {doc['document_type'] for doc in received_documents}
        missing_docs = [
            {
                'type': doc['document_type'],
                'source': doc.get('source', 'Unknown'),
                'required': doc.get('required', False)
            }
            for doc in required_documents
            if doc['document_type'] not in received_types
        ]
        
        # Determine status
        if completion_pct == 100:
            status = 'complete'
        elif completion_pct >= 50:
            status = 'incomplete'
        else:
            status = 'at_risk'
        
        # Build response
        response = {
            'client_id': client_id,
            'tax_year': tax_year,
            'status': status,
            'completion_percentage': completion_pct,
            'required_documents': [
                {
                    'type': doc['document_type'],
                    'source': doc.get('source', 'Unknown'),
                    'received': doc['document_type'] in received_types,
                    'last_checked': datetime.utcnow().isoformat()
                }
                for doc in required_documents
            ],
            'received_documents': received_documents,
            'missing_documents': missing_docs,
            'last_checked': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Document check complete: {completion_pct}% complete")
        
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
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }
            ]
        }
```

**Tool Spec:** `gateway/tools/document_checker/tool_spec.json`

```json
{
  "name": "check_client_documents",
  "description": "Scan client folder and identify missing tax documents. Returns completion status, list of received documents, and list of missing documents.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "client_id": {
        "type": "string",
        "description": "Unique client identifier (UUID format)"
      },
      "tax_year": {
        "type": "integer",
        "description": "Tax year to check (e.g., 2024)"
      }
    },
    "required": ["client_id", "tax_year"]
  }
}
```

---

### Tool 2: Email Sender Lambda

**Purpose:** Send personalized follow-up emails via AWS SES

**File:** `gateway/tools/email_sender/email_sender_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
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
SETTINGS_TABLE = os.environ['SETTINGS_TABLE']
SES_FROM_EMAIL = os.environ['SES_FROM_EMAIL']


def get_client_info(client_id: str) -> Dict[str, Any]:
    """
    Get client information from DynamoDB.
    
    Args:
        client_id: Unique client identifier
    
    Returns:
        Client information dictionary
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


def get_email_template(
    accountant_id: str,
    followup_number: int
) -> Dict[str, str]:
    """
    Get email template from accountant settings.
    
    Args:
        accountant_id: Accountant identifier
        followup_number: Which reminder (1, 2, 3, etc.)
    
    Returns:
        Dictionary with subject and body templates
    """
    table = dynamodb.Table(SETTINGS_TABLE)
    
    try:
        response = table.get_item(
            Key={
                'accountant_id': accountant_id,
                'settings_type': 'email_templates'
            }
        )
        
        if 'Item' not in response:
            # Return default templates
            return get_default_template(followup_number)
        
        templates = response['Item'].get('templates', {})
        template_key = f'reminder_{followup_number}'
        
        if template_key not in templates:
            return get_default_template(followup_number)
        
        return templates[template_key]
        
    except ClientError as e:
        logger.error(f"Error getting email template: {e}")
        return get_default_template(followup_number)


def get_default_template(followup_number: int) -> Dict[str, str]:
    """
    Get default email template.
    
    Args:
        followup_number: Which reminder (1, 2, 3, etc.)
    
    Returns:
        Dictionary with subject and body templates
    """
    templates = {
        1: {
            'subject': 'Documents needed for your {tax_year} tax return',
            'body': '''Dear {client_name},

I hope this email finds you well. I'm reaching out regarding your {tax_year} tax return.

To complete your return, I still need the following documents:

{missing_documents_list}

Please upload these documents to your secure client portal at your earliest convenience. If you have any questions or need assistance, please don't hesitate to reach out.

Thank you for your prompt attention to this matter.

Best regards,
{accountant_name}
{accountant_firm}'''
        },
        2: {
            'subject': 'Reminder: Documents still needed for your {tax_year} tax return',
            'body': '''Dear {client_name},

This is a friendly reminder that I'm still waiting for the following documents to complete your {tax_year} tax return:

{missing_documents_list}

The tax filing deadline is approaching, and I want to ensure we have enough time to prepare your return accurately. Please upload these documents as soon as possible.

If you're having trouble locating any of these documents, please let me know and I'll be happy to help.

Best regards,
{accountant_name}
{accountant_firm}'''
        },
        3: {
            'subject': 'URGENT: Documents needed to avoid tax filing delays',
            'body': '''Dear {client_name},

This is my third request for the following documents needed to complete your {tax_year} tax return:

{missing_documents_list}

Without these documents, I cannot file your return on time, which may result in penalties and interest charges. Please treat this as urgent and upload the documents immediately.

If you need assistance or have questions, please call me directly at {accountant_phone}.

Sincerely,
{accountant_name}
{accountant_firm}'''
        }
    }
    
    return templates.get(followup_number, templates[1])


def format_missing_documents(missing_docs: List[str]) -> str:
    """
    Format missing documents list for email.
    
    Args:
        missing_docs: List of missing document types
    
    Returns:
        Formatted string for email body
    """
    if not missing_docs:
        return "None - all documents received!"
    
    formatted = []
    for i, doc in enumerate(missing_docs, 1):
        formatted.append(f"{i}. {doc}")
    
    return "\n".join(formatted)


def personalize_email(
    template: Dict[str, str],
    client_info: Dict[str, Any],
    missing_docs: List[str],
    tax_year: int
) -> Dict[str, str]:
    """
    Personalize email template with client data.
    
    Args:
        template: Email template dictionary
        client_info: Client information
        missing_docs: List of missing documents
        tax_year: Tax year
    
    Returns:
        Dictionary with personalized subject and body
    """
    # Format missing documents
    missing_docs_list = format_missing_documents(missing_docs)
    
    # Replacement values
    replacements = {
        '{client_name}': client_info.get('client_name', 'Valued Client'),
        '{tax_year}': str(tax_year),
        '{missing_documents_list}': missing_docs_list,
        '{accountant_name}': client_info.get('accountant_name', 'Your Accountant'),
        '{accountant_firm}': client_info.get('accountant_firm', ''),
        '{accountant_phone}': client_info.get('accountant_phone', ''),
    }
    
    # Apply replacements
    subject = template['subject']
    body = template['body']
    
    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value)
        body = body.replace(placeholder, value)
    
    return {
        'subject': subject,
        'body': body
    }


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
        logger.info(f"Email sent successfully: {message_id}")
        
        return message_id
        
    except ClientError as e:
        logger.error(f"Error sending email via SES: {e}")
        raise


def log_followup(
    client_id: str,
    followup_number: int,
    email_subject: str,
    email_body: str,
    missing_docs: List[str],
    accountant_id: str
) -> str:
    """
    Log follow-up to DynamoDB.
    
    Args:
        client_id: Client identifier
        followup_number: Which reminder
        email_subject: Email subject sent
        email_body: Email body sent
        missing_docs: List of missing documents
        accountant_id: Accountant identifier
    
    Returns:
        Follow-up ID
    """
    table = dynamodb.Table(FOLLOWUP_TABLE)
    
    followup_id = f"fu_{int(datetime.utcnow().timestamp())}"
    sent_date = datetime.utcnow().isoformat()
    
    # Calculate next follow-up date (7 days from now)
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
    """
    Lambda handler for sending follow-up emails.
    
    Args:
        event: Lambda event containing email parameters
        context: Lambda context object
    
    Returns:
        Dictionary with email sending confirmation
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
        missing_documents = event.get('missing_documents', [])
        followup_number = event.get('followup_number', 1)
        custom_message = event.get('custom_message')
        
        if not client_id or not missing_documents:
            raise ValueError("Missing required parameters: client_id, missing_documents")
        
        # Get client information
        client_info = get_client_info(client_id)
        accountant_id = client_info.get('accountant_id')
        tax_year = client_info.get('tax_year', datetime.now().year)
        
        # Get email template
        template = get_email_template(accountant_id, followup_number)
        
        # Personalize email
        personalized = personalize_email(
            template=template,
            client_info=client_info,
            missing_docs=missing_documents,
            tax_year=tax_year
        )
        
        # Add custom message if provided
        if custom_message:
            personalized['body'] = f"{custom_message}\n\n{personalized['body']}"
        
        # Send email
        message_id = send_email_via_ses(
            to_email=client_info['email'],
            subject=personalized['subject'],
            body=personalized['body']
        )
        
        # Log follow-up
        followup_id = log_followup(
            client_id=client_id,
            followup_number=followup_number,
            email_subject=personalized['subject'],
            email_body=personalized['body'],
            missing_docs=missing_documents,
            accountant_id=accountant_id
        )
        
        # Calculate next follow-up date
        next_followup = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        # Build response
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

**Tool Spec:** `gateway/tools/email_sender/tool_spec.json`

```json
{
  "name": "send_followup_email",
  "description": "Send personalized follow-up email to client requesting missing tax documents. Automatically logs the follow-up and schedules next reminder.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "client_id": {
        "type": "string",
        "description": "Unique client identifier"
      },
      "missing_documents": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "List of missing document types (e.g., ['W-2', '1099-INT'])"
      },
      "followup_number": {
        "type": "integer",
        "description": "Which reminder this is (1, 2, 3, etc.)",
        "minimum": 1,
        "maximum": 10
      },
      "custom_message": {
        "type": "string",
        "description": "Optional custom message to prepend to email"
      }
    },
    "required": ["client_id", "missing_documents", "followup_number"]
  }
}
```



---

### Tool 3: Status Tracker Lambda

**Purpose:** Get comprehensive status for clients

**File:** `gateway/tools/status_tracker/status_tracker_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']
FOLLOWUP_TABLE = os.environ['FOLLOWUP_TABLE']
SETTINGS_TABLE = os.environ['SETTINGS_TABLE']


def get_accountant_settings(accountant_id: str) -> Dict[str, Any]:
    """
    Get accountant settings including follow-up schedule.
    
    Args:
        accountant_id: Accountant identifier
    
    Returns:
        Settings dictionary
    """
    table = dynamodb.Table(SETTINGS_TABLE)
    
    try:
        response = table.get_item(
            Key={
                'accountant_id': accountant_id,
                'settings_type': 'preferences'
            }
        )
        
        if 'Item' in response:
            return response['Item']
        
        # Return defaults
        return {
            'followup_schedule': [3, 7, 14],  # Days between reminders
            'escalation_threshold': 3,  # Number of reminders before escalation
            'escalation_days': 2,  # Days before escalation after last reminder
        }
        
    except ClientError as e:
        logger.error(f"Error getting settings: {e}")
        return {}


def get_all_clients(accountant_id: str) -> List[Dict[str, Any]]:
    """
    Get all clients for an accountant.
    
    Args:
        accountant_id: Accountant identifier
    
    Returns:
        List of client dictionaries
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    try:
        # Query using GSI on accountant_id
        response = table.query(
            IndexName='accountant-index',
            KeyConditionExpression=Key('accountant_id').eq(accountant_id)
        )
        
        return response.get('Items', [])
        
    except ClientError as e:
        logger.error(f"Error querying clients: {e}")
        raise


def get_client_documents(client_id: str) -> Dict[str, Any]:
    """
    Get document status for a client.
    
    Args:
        client_id: Client identifier
    
    Returns:
        Dictionary with document counts and status
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression=Key('client_id').eq(client_id)
        )
        
        documents = response.get('Items', [])
        
        required_docs = [d for d in documents if d.get('required', False)]
        received_docs = [d for d in documents if d.get('received', False)]
        
        total_required = len(required_docs)
        total_received = len(received_docs)
        
        completion_pct = 0
        if total_required > 0:
            completion_pct = int((total_received / total_required) * 100)
        
        missing_docs = [
            d['document_type']
            for d in required_docs
            if not d.get('received', False)
        ]
        
        return {
            'total_required': total_required,
            'total_received': total_received,
            'completion_percentage': completion_pct,
            'missing_documents': missing_docs
        }
        
    except ClientError as e:
        logger.error(f"Error getting documents: {e}")
        return {
            'total_required': 0,
            'total_received': 0,
            'completion_percentage': 0,
            'missing_documents': []
        }


def get_followup_history(client_id: str) -> Dict[str, Any]:
    """
    Get follow-up history for a client.
    
    Args:
        client_id: Client identifier
    
    Returns:
        Dictionary with follow-up information
    """
    table = dynamodb.Table(FOLLOWUP_TABLE)
    
    try:
        response = table.query(
            KeyConditionExpression=Key('client_id').eq(client_id),
            ScanIndexForward=False,  # Most recent first
            Limit=10
        )
        
        followups = response.get('Items', [])
        
        if not followups:
            return {
                'followup_count': 0,
                'last_followup': None,
                'last_followup_date': None,
                'next_followup_date': None
            }
        
        last_followup = followups[0]
        
        return {
            'followup_count': len(followups),
            'last_followup': last_followup.get('followup_number', 0),
            'last_followup_date': last_followup.get('sent_date'),
            'next_followup_date': last_followup.get('next_followup_date'),
            'response_received': last_followup.get('response_received', False)
        }
        
    except ClientError as e:
        logger.error(f"Error getting follow-up history: {e}")
        return {
            'followup_count': 0,
            'last_followup': None,
            'last_followup_date': None,
            'next_followup_date': None
        }


def calculate_risk_status(
    completion_pct: int,
    followup_count: int,
    last_followup_date: Optional[str],
    settings: Dict[str, Any]
) -> str:
    """
    Calculate client risk status.
    
    Args:
        completion_pct: Document completion percentage
        followup_count: Number of follow-ups sent
        last_followup_date: Date of last follow-up
        settings: Accountant settings
    
    Returns:
        Status string: 'complete', 'incomplete', 'at_risk', 'escalated'
    """
    if completion_pct == 100:
        return 'complete'
    
    escalation_threshold = settings.get('escalation_threshold', 3)
    escalation_days = settings.get('escalation_days', 2)
    
    # Check if escalation threshold reached
    if followup_count >= escalation_threshold:
        # Check if enough time has passed since last follow-up
        if last_followup_date:
            last_date = datetime.fromisoformat(last_followup_date)
            days_since = (datetime.utcnow() - last_date).days
            
            if days_since >= escalation_days:
                return 'escalated'
        
        return 'at_risk'
    
    # Check if approaching escalation
    if followup_count >= (escalation_threshold - 1):
        return 'at_risk'
    
    return 'incomplete'


def calculate_days_until_escalation(
    followup_count: int,
    last_followup_date: Optional[str],
    settings: Dict[str, Any]
) -> Optional[int]:
    """
    Calculate days until escalation.
    
    Args:
        followup_count: Number of follow-ups sent
        last_followup_date: Date of last follow-up
        settings: Accountant settings
    
    Returns:
        Days until escalation, or None if not applicable
    """
    escalation_threshold = settings.get('escalation_threshold', 3)
    escalation_days = settings.get('escalation_days', 2)
    
    if followup_count < escalation_threshold:
        return None
    
    if not last_followup_date:
        return 0
    
    last_date = datetime.fromisoformat(last_followup_date)
    escalation_date = last_date + timedelta(days=escalation_days)
    days_until = (escalation_date - datetime.utcnow()).days
    
    return max(0, days_until)


def build_client_status(
    client: Dict[str, Any],
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build comprehensive status for a client.
    
    Args:
        client: Client information
        settings: Accountant settings
    
    Returns:
        Complete client status dictionary
    """
    client_id = client['client_id']
    
    # Get document status
    doc_status = get_client_documents(client_id)
    
    # Get follow-up history
    followup_status = get_followup_history(client_id)
    
    # Calculate risk status
    status = calculate_risk_status(
        completion_pct=doc_status['completion_percentage'],
        followup_count=followup_status['followup_count'],
        last_followup_date=followup_status['last_followup_date'],
        settings=settings
    )
    
    # Calculate days until escalation
    days_until_escalation = calculate_days_until_escalation(
        followup_count=followup_status['followup_count'],
        last_followup_date=followup_status['last_followup_date'],
        settings=settings
    )
    
    # Determine next action
    next_action = determine_next_action(
        status=status,
        followup_count=followup_status['followup_count'],
        next_followup_date=followup_status['next_followup_date']
    )
    
    return {
        'client_id': client_id,
        'client_name': client.get('client_name', 'Unknown'),
        'email': client.get('email', ''),
        'status': status,
        'completion_percentage': doc_status['completion_percentage'],
        'total_required': doc_status['total_required'],
        'total_received': doc_status['total_received'],
        'missing_documents': doc_status['missing_documents'],
        'followup_count': followup_status['followup_count'],
        'last_followup': followup_status['last_followup'],
        'last_followup_date': followup_status['last_followup_date'],
        'next_followup_date': followup_status['next_followup_date'],
        'days_until_escalation': days_until_escalation,
        'next_action': next_action
    }


def determine_next_action(
    status: str,
    followup_count: int,
    next_followup_date: Optional[str]
) -> str:
    """
    Determine next action for client.
    
    Args:
        status: Client status
        followup_count: Number of follow-ups
        next_followup_date: Date of next scheduled follow-up
    
    Returns:
        Next action description
    """
    if status == 'complete':
        return 'No action needed - all documents received'
    
    if status == 'escalated':
        return 'Requires accountant intervention - call client directly'
    
    if status == 'at_risk':
        if next_followup_date:
            return f"Send reminder #{followup_count + 1} on {next_followup_date[:10]}"
        return f"Send reminder #{followup_count + 1} immediately"
    
    # Incomplete
    if next_followup_date:
        return f"Send reminder #{followup_count + 1} on {next_followup_date[:10]}"
    
    return "Send initial document request"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for getting client status.
    
    Args:
        event: Lambda event containing query parameters
        context: Lambda context object
    
    Returns:
        Dictionary with client status information
    """
    try:
        # Extract tool name from context
        delimiter = "___"
        original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        tool_name = original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
        
        logger.info(f"Tool invoked: {tool_name}")
        logger.info(f"Event: {json.dumps(event)}")
        
        # Extract parameters
        accountant_id = event.get('accountant_id')
        client_id = event.get('client_id', 'all')
        status_filter = event.get('filter', 'all')
        
        if not accountant_id:
            raise ValueError("Missing required parameter: accountant_id")
        
        # Get accountant settings
        settings = get_accountant_settings(accountant_id)
        
        # Get clients
        if client_id == 'all':
            clients = get_all_clients(accountant_id)
        else:
            # Get single client
            table = dynamodb.Table(CLIENTS_TABLE)
            response = table.get_item(Key={'client_id': client_id})
            
            if 'Item' not in response:
                raise ValueError(f"Client not found: {client_id}")
            
            clients = [response['Item']]
        
        # Build status for each client
        client_statuses = []
        for client in clients:
            client_status = build_client_status(client, settings)
            
            # Apply filter
            if status_filter == 'all' or client_status['status'] == status_filter:
                client_statuses.append(client_status)
        
        # Calculate summary
        summary = {
            'total_clients': len(client_statuses),
            'complete': len([c for c in client_statuses if c['status'] == 'complete']),
            'incomplete': len([c for c in client_statuses if c['status'] == 'incomplete']),
            'at_risk': len([c for c in client_statuses if c['status'] == 'at_risk']),
            'escalated': len([c for c in client_statuses if c['status'] == 'escalated'])
        }
        
        # Sort by priority (escalated first, then at_risk, etc.)
        priority_order = {'escalated': 0, 'at_risk': 1, 'incomplete': 2, 'complete': 3}
        client_statuses.sort(key=lambda x: priority_order.get(x['status'], 4))
        
        # Build response
        response = {
            'summary': summary,
            'clients': client_statuses,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Status retrieved for {len(client_statuses)} clients")
        
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
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }
            ]
        }
```

**Tool Spec:** `gateway/tools/status_tracker/tool_spec.json`

```json
{
  "name": "get_client_status",
  "description": "Get comprehensive status for one or all clients. Returns summary statistics and detailed status for each client including completion percentage, follow-up history, and next actions.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "accountant_id": {
        "type": "string",
        "description": "Accountant identifier to filter clients"
      },
      "client_id": {
        "type": "string",
        "description": "Specific client ID, or 'all' for all clients (default: 'all')"
      },
      "filter": {
        "type": "string",
        "enum": ["all", "complete", "incomplete", "at_risk", "escalated"],
        "description": "Filter clients by status (default: 'all')"
      }
    },
    "required": ["accountant_id"]
  }
}
```

---

## Part 2: CDK Infrastructure Implementation

### Complete Backend Stack

**File:** `infra-cdk/lib/tax-agent-backend-stack.ts`

```typescript
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import * as bedrockagentcore from '@aws-cdk/aws-bedrock-agentcore-alpha';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';
import * as path from 'path';

export interface TaxAgentBackendStackProps extends cdk.StackProps {
  stackNameBase: string;
  cognitoUserPoolId: string;
  cognitoUserPoolArn: string;
  cognitoClientId: string;
  cognitoDomain: string;
  sesFromEmail: string;
}

export class TaxAgentBackendStack extends cdk.Stack {
  public readonly runtimeArn: string;
  public readonly memoryId: string;
  public readonly gatewayUrl: string;

  constructor(scope: Construct, id: string, props: TaxAgentBackendStackProps) {
    super(scope, id, props);

    // ========================================
    // DynamoDB Tables with Cost Optimization
    // ========================================

    // Clients Table
    const clientsTable = new dynamodb.Table(this, 'ClientsTable', {
      tableName: `${props.stackNameBase}-clients`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tax_year', type: dynamodb.AttributeType.NUMBER },
      
      // Provisioned capacity for cost optimization
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      
      // Auto-scaling
      autoScaleReadCapacity: {
        minCapacity: 1,
        maxCapacity: 5,
        targetUtilizationPercent: 70,
      },
      autoScaleWriteCapacity: {
        minCapacity: 1,
        maxCapacity: 3,
        targetUtilizationPercent: 70,
      },
      
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // GSI for querying by accountant
    clientsTable.addGlobalSecondaryIndex({
      indexName: 'accountant-index',
      partitionKey: { name: 'accountant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      readCapacity: 1,
      writeCapacity: 1,
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Document Requirements Table
    const documentsTable = new dynamodb.Table(this, 'DocumentsTable', {
      tableName: `${props.stackNameBase}-documents`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'document_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      autoScaleReadCapacity: {
        minCapacity: 1,
        maxCapacity: 5,
        targetUtilizationPercent: 70,
      },
      autoScaleWriteCapacity: {
        minCapacity: 1,
        maxCapacity: 3,
        targetUtilizationPercent: 70,
      },
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Follow-up History Table
    const followupTable = new dynamodb.Table(this, 'FollowupTable', {
      tableName: `${props.stackNameBase}-followups`,
      partitionKey: { name: 'client_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'followup_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      autoScaleReadCapacity: {
        minCapacity: 1,
        maxCapacity: 5,
        targetUtilizationPercent: 70,
      },
      autoScaleWriteCapacity: {
        minCapacity: 1,
        maxCapacity: 3,
        targetUtilizationPercent: 70,
      },
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Accountant Settings Table
    const settingsTable = new dynamodb.Table(this, 'SettingsTable', {
      tableName: `${props.stackNameBase}-settings`,
      partitionKey: { name: 'accountant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'settings_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 1,
      writeCapacity: 1,
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ========================================
    // S3 Bucket for Client Documents
    // ========================================

    const clientBucket = new s3.Bucket(this, 'ClientDocuments', {
      bucketName: `${props.stackNameBase}-client-docs`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      
      // Intelligent tiering for cost optimization
      intelligentTieringConfigurations: [{
        name: 'TaxDocumentTiering',
        archiveAccessTierTime: cdk.Duration.days(90),
        deepArchiveAccessTierTime: cdk.Duration.days(180),
      }],
      
      // Lifecycle rules
      lifecycleRules: [
        {
          // Move to Glacier after tax season
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(120),
            },
            {
              storageClass: s3.StorageClass.DEEP_ARCHIVE,
              transitionAfter: cdk.Duration.days(365),
            }
          ],
          expiration: cdk.Duration.days(2555), // 7 years
        }
      ],
      
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ========================================
    // Gateway Lambda Functions
    // ========================================

    // Shared Lambda layer for common dependencies
    const commonLayer = new lambda.LayerVersion(this, 'CommonLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/layers/common')),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Common utilities for Gateway tools',
    });

    // Document Checker Lambda
    const documentCheckerLambda = new lambda.Function(this, 'DocumentChecker', {
      functionName: `${props.stackNameBase}-document-checker`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'document_checker_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/document_checker')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64, // Cost optimization
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: clientsTable.tableName,
        DOCUMENTS_TABLE: documentsTable.tableName,
        CLIENT_BUCKET: clientBucket.bucketName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH, // Cost optimization
    });

    // Grant permissions
    clientsTable.grantReadData(documentCheckerLambda);
    documentsTable.grantReadWriteData(documentCheckerLambda);
    clientBucket.grantRead(documentCheckerLambda);

    // Email Sender Lambda
    const emailSenderLambda = new lambda.Function(this, 'EmailSender', {
      functionName: `${props.stackNameBase}-email-sender`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'email_sender_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/email_sender')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: clientsTable.tableName,
        FOLLOWUP_TABLE: followupTable.tableName,
        SETTINGS_TABLE: settingsTable.tableName,
        SES_FROM_EMAIL: props.sesFromEmail,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    // Grant permissions
    clientsTable.grantReadData(emailSenderLambda);
    followupTable.grantReadWriteData(emailSenderLambda);
    settingsTable.grantReadData(emailSenderLambda);
    
    // SES permissions
    emailSenderLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // Status Tracker Lambda
    const statusTrackerLambda = new lambda.Function(this, 'StatusTracker', {
      functionName: `${props.stackNameBase}-status-tracker`,
      runtime: lambda.Runtime.PYTHON_3_13,
      handler: 'status_tracker_lambda.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/status_tracker')),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      layers: [commonLayer],
      environment: {
        CLIENTS_TABLE: clientsTable.tableName,
        DOCUMENTS_TABLE: documentsTable.tableName,
        FOLLOWUP_TABLE: followupTable.tableName,
        SETTINGS_TABLE: settingsTable.tableName,
      },
      logRetention: logs.RetentionDays.ONE_MONTH,
    });

    // Grant permissions
    clientsTable.grantReadData(statusTrackerLambda);
    documentsTable.grantReadData(statusTrackerLambda);
    followupTable.grantReadData(statusTrackerLambda);
    settingsTable.grantReadData(statusTrackerLambda);

    // Continue in next part...
  }
}
```

I'll continue with the remaining CDK infrastructure, frontend components, and testing in the next section. Would you like me to continue with:

1. Complete CDK stack (Gateway, AgentCore Runtime, EventBridge)
2. Frontend React components (Dashboard, Client Detail, Email Templates)
3. Testing scripts and utilities
4. Deployment automation

Which would you like me to dive into next?

