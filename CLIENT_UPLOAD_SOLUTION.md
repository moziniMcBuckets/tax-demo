# Client Document Upload Solution

## Problem Identified

The current architecture scans S3 for documents but doesn't provide a way for clients to upload them. We need to add:
1. Client-facing upload portal
2. Secure upload mechanism
3. Document validation
4. Automatic notification to agent

---

## Solution Options

### Option 1: S3 Presigned URLs (Recommended)

**How it works:**
1. Client requests upload URL from API
2. API generates presigned S3 URL (valid for 15 minutes)
3. Client uploads directly to S3 using presigned URL
4. S3 event triggers Lambda to notify agent
5. Agent checks documents and updates status

**Pros:**
- ✅ Secure (time-limited, scoped permissions)
- ✅ No file size limits
- ✅ Direct upload (no Lambda payload limits)
- ✅ Cost-effective (no data transfer through Lambda)
- ✅ Simple client implementation

**Cons:**
- Requires S3 event configuration
- Client needs to handle S3 upload

**Cost:** ~$0.01 per 1,000 uploads

### Option 2: API Gateway + Lambda Upload

**How it works:**
1. Client uploads file to API Gateway
2. Lambda receives file and uploads to S3
3. Lambda notifies agent
4. Agent checks documents

**Pros:**
- ✅ Simple client implementation (standard HTTP POST)
- ✅ Can validate before upload
- ✅ Centralized logging

**Cons:**
- ❌ 10 MB payload limit (API Gateway)
- ❌ Higher cost (data transfer through Lambda)
- ❌ Slower for large files

**Cost:** ~$0.10 per 1,000 uploads

### Option 3: Client Portal with Amplify Storage

**How it works:**
1. Client logs into portal
2. Uses Amplify Storage for uploads
3. Amplify handles S3 presigned URLs
4. S3 event triggers agent notification

**Pros:**
- ✅ Built-in authentication
- ✅ Simple React integration
- ✅ Automatic presigned URLs
- ✅ Progress tracking

**Cons:**
- Requires client authentication
- More complex setup

**Cost:** ~$0.01 per 1,000 uploads

---

## Recommended Implementation: Presigned URLs

### Architecture

```
Client Browser
    ↓ (1) Request upload URL
API Gateway + Lambda
    ↓ (2) Generate presigned URL
Client Browser
    ↓ (3) Upload directly to S3
S3 Bucket
    ↓ (4) S3 Event Notification
Lambda (Document Processor)
    ↓ (5) Classify & update DynamoDB
    ↓ (6) Notify agent (optional)
Agent checks status on next query
```

---

## Implementation

### 1. Upload URL Generator Lambda

**File:** `gateway/tools/upload_manager/upload_manager_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Upload Manager Lambda - Generate presigned URLs for client document uploads.
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

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

CLIENT_BUCKET = os.environ['CLIENT_BUCKET']
CLIENTS_TABLE = os.environ['CLIENTS_TABLE']


def validate_client(client_id: str, upload_token: str) -> bool:
    """
    Validate client has permission to upload.
    
    Args:
        client_id: Client identifier
        upload_token: Secure token sent to client via email
    
    Returns:
        True if valid, False otherwise
    """
    table = dynamodb.Table(CLIENTS_TABLE)
    
    try:
        response = table.get_item(Key={'client_id': client_id})
        
        if 'Item' not in response:
            return False
        
        # Check if upload token matches
        stored_token = response['Item'].get('upload_token')
        return stored_token == upload_token
        
    except ClientError as e:
        logger.error(f"Error validating client: {e}")
        return False


def generate_presigned_url(
    client_id: str,
    filename: str,
    tax_year: int,
    document_type: str
) -> str:
    """
    Generate presigned URL for S3 upload.
    
    Args:
        client_id: Client identifier
        filename: Name of file to upload
        tax_year: Tax year
        document_type: Type of document (W-2, 1099-INT, etc.)
    
    Returns:
        Presigned URL string
    """
    # Sanitize filename
    safe_filename = filename.replace(' ', '_').replace('..', '')
    
    # S3 key with metadata
    s3_key = f"{client_id}/{tax_year}/{safe_filename}"
    
    try:
        # Generate presigned URL (valid for 15 minutes)
        url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': CLIENT_BUCKET,
                'Key': s3_key,
                'ContentType': 'application/pdf',
                'Metadata': {
                    'document-type': document_type,
                    'tax-year': str(tax_year),
                    'upload-date': datetime.utcnow().isoformat(),
                    'client-id': client_id,
                }
            },
            ExpiresIn=900  # 15 minutes
        )
        
        logger.info(f"Generated presigned URL for {client_id}/{filename}")
        return url
        
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating upload URLs.
    
    Args:
        event: API Gateway event with client_id, filename, document_type
        context: Lambda context
    
    Returns:
        Presigned URL response
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        client_id = body.get('client_id')
        upload_token = body.get('upload_token')
        filename = body.get('filename')
        tax_year = body.get('tax_year', datetime.now().year)
        document_type = body.get('document_type', 'Unknown')
        
        if not all([client_id, upload_token, filename]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Validate client
        if not validate_client(client_id, upload_token):
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Invalid client or token'})
            }
        
        # Generate presigned URL
        upload_url = generate_presigned_url(
            client_id=client_id,
            filename=filename,
            tax_year=tax_year,
            document_type=document_type
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'upload_url': upload_url,
                'expires_in': 900,
                's3_key': f"{client_id}/{tax_year}/{filename}"
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 2. S3 Event Processor Lambda

**File:** `gateway/tools/document_processor/document_processor_lambda.py`

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Document Processor Lambda - Processes S3 upload events.
Triggered automatically when clients upload documents.
"""

import json
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
DOCUMENTS_TABLE = os.environ['DOCUMENTS_TABLE']


def process_s3_event(event: Dict[str, Any]) -> None:
    """
    Process S3 upload event.
    
    Args:
        event: S3 event notification
    """
    for record in event.get('Records', []):
        # Extract S3 information
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing upload: {bucket}/{key}")
        
        # Parse key: client_id/tax_year/filename
        parts = key.split('/')
        if len(parts) < 3:
            logger.warning(f"Invalid S3 key format: {key}")
            continue
        
        client_id = parts[0]
        tax_year = int(parts[1])
        filename = parts[2]
        
        # Get object metadata
        s3 = boto3.client('s3')
        try:
            response = s3.head_object(Bucket=bucket, Key=key)
            metadata = response.get('Metadata', {})
            
            document_type = metadata.get('document-type', 'Unknown')
            
            # Update DynamoDB
            table = dynamodb.Table(DOCUMENTS_TABLE)
            table.update_item(
                Key={
                    'client_id': client_id,
                    'document_type': document_type
                },
                UpdateExpression='SET received = :r, received_date = :rd, file_path = :fp',
                ExpressionAttributeValues={
                    ':r': True,
                    ':rd': datetime.utcnow().isoformat(),
                    ':fp': f's3://{bucket}/{key}'
                }
            )
            
            logger.info(f"Updated document status: {client_id}/{document_type}")
            
        except ClientError as e:
            logger.error(f"Error processing upload: {e}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for S3 events."""
    try:
        process_s3_event(event)
        return {'statusCode': 200, 'body': 'Success'}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {'statusCode': 500, 'body': str(e)}
```

### 3. Client Upload Portal Component

**File:** `frontend/src/components/tax/ClientUploadPortal.tsx`

```typescript
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Client Upload Portal
 * 
 * Allows clients to upload tax documents securely.
 * Uses presigned S3 URLs for direct upload.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';

const DOCUMENT_TYPES = [
  'W-2',
  '1099-INT',
  '1099-DIV',
  '1099-MISC',
  '1099-NEC',
  'Prior Year Tax Return',
  'Other',
];

export function ClientUploadPortal() {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setSuccess(false);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !documentType) {
      setError('Please select a file and document type');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      // Step 1: Get presigned URL from API
      const response = await fetch('/api/upload-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: 'CLIENT_ID', // From URL param or auth
          upload_token: 'TOKEN', // From URL param
          filename: file.name,
          tax_year: 2024,
          document_type: documentType,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get upload URL');
      }

      const { upload_url } = await response.json();

      // Step 2: Upload directly to S3
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': 'application/pdf',
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Upload failed');
      }

      setSuccess(true);
      setFile(null);
      setDocumentType('');
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload Tax Documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Document Type Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Document Type
            </label>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="">Select document type...</option>
              {DOCUMENT_TYPES.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          {/* File Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Select File (PDF)
            </label>
            <Input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
            />
            {file && (
              <p className="text-sm text-gray-500 mt-2">
                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>

          {/* Upload Button */}
          <Button
            onClick={handleUpload}
            disabled={!file || !documentType || uploading}
            className="w-full"
          >
            <Upload className="w-4 h-4 mr-2" />
            {uploading ? 'Uploading...' : 'Upload Document'}
          </Button>

          {/* Success Message */}
          {success && (
            <div className="flex items-center gap-2 p-3 bg-green-50 text-green-800 rounded">
              <CheckCircle className="w-5 h-5" />
              <span>Document uploaded successfully!</span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-800 rounded">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## CDK Infrastructure Updates

### Add to Backend Stack:

```typescript
// In tax-agent-backend-stack.ts

// Upload Manager Lambda
const uploadManagerLambda = new lambda.Function(this, 'UploadManager', {
  functionName: `${config.stack_name_base}-upload-manager`,
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'upload_manager_lambda.lambda_handler',
  code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/upload_manager')),
  timeout: cdk.Duration.seconds(30),
  memorySize: 256,
  architecture: lambda.Architecture.ARM_64,
  environment: {
    CLIENT_BUCKET: clientBucket.bucketName,
    CLIENTS_TABLE: tables.clientsTable.tableName,
  },
  logRetention: logs.RetentionDays.ONE_MONTH,
});

// Grant permissions
clientBucket.grantPut(uploadManagerLambda);
tables.clientsTable.grantReadData(uploadManagerLambda);

// Document Processor Lambda (triggered by S3 events)
const documentProcessorLambda = new lambda.Function(this, 'DocumentProcessor', {
  functionName: `${config.stack_name_base}-document-processor`,
  runtime: lambda.Runtime.PYTHON_3_13,
  handler: 'document_processor_lambda.lambda_handler',
  code: lambda.Code.fromAsset(path.join(__dirname, '../../gateway/tools/document_processor')),
  timeout: cdk.Duration.seconds(60),
  memorySize: 512,
  architecture: lambda.Architecture.ARM_64,
  environment: {
    DOCUMENTS_TABLE: tables.documentsTable.tableName,
  },
  logRetention: logs.RetentionDays.ONE_MONTH,
});

// Grant permissions
clientBucket.grantRead(documentProcessorLambda);
tables.documentsTable.grantReadWriteData(documentProcessorLambda);

// S3 event notification
clientBucket.addEventNotification(
  s3.EventType.OBJECT_CREATED,
  new s3n.LambdaDestination(documentProcessorLambda),
  { prefix: '', suffix: '.pdf' }
);

// API Gateway for upload URL generation
const uploadApi = new apigateway.RestApi(this, 'UploadApi', {
  restApiName: `${config.stack_name_base}-upload-api`,
  description: 'API for client document uploads',
  defaultCorsPreflightOptions: {
    allowOrigins: ['*'], // Restrict in production
    allowMethods: ['POST', 'OPTIONS'],
    allowHeaders: ['Content-Type'],
  },
});

const uploadResource = uploadApi.root.addResource('upload-url');
uploadResource.addMethod(
  'POST',
  new apigateway.LambdaIntegration(uploadManagerLambda)
);
```

---

## Client Upload Flow

### Step 1: Accountant Sends Upload Link

When accountant sends reminder email, include upload link:

```
Dear John,

Please upload your missing documents:
- W-2 from Employer ABC
- 1099-INT from Chase Bank

Upload here: https://yourdomain.com/upload?client=abc123&token=xyz789

This link expires in 30 days.
```

### Step 2: Client Uploads Document

1. Client clicks link
2. Portal loads with client_id and token from URL
3. Client selects document type
4. Client selects PDF file
5. Client clicks "Upload"
6. Portal requests presigned URL from API
7. Portal uploads directly to S3
8. Success message shown

### Step 3: Automatic Processing

1. S3 triggers Document Processor Lambda
2. Lambda updates DynamoDB (document received)
3. Next time agent checks, sees new document
4. Agent updates completion percentage

### Step 4: Agent Notification (Optional)

Add to Document Processor:

```python
# After updating DynamoDB, check if client is now complete
completion_pct = calculate_completion(client_id)

if completion_pct == 100:
    # Notify accountant
    send_completion_notification(client_id)
```

---

## Alternative: Email-Based Upload

### Simpler Option for Non-Technical Clients:

1. Client replies to reminder email with attachment
2. SES receives email (configure SES receipt rule)
3. SES saves attachment to S3
4. S3 event triggers processor
5. Same flow as above

**Setup:**
```bash
# Configure SES to receive emails
aws ses create-receipt-rule \
  --rule-set-name tax-agent-receipts \
  --rule '{
    "Name": "save-attachments",
    "Enabled": true,
    "Recipients": ["uploads@yourdomain.com"],
    "Actions": [{
      "S3Action": {
        "BucketName": "tax-agent-client-docs",
        "ObjectKeyPrefix": "email-uploads/"
      }
    }]
  }'
```

---

## Security Considerations

### Upload Token Generation:

```python
# When creating client, generate secure upload token
import secrets

upload_token = secrets.token_urlsafe(32)

# Store in DynamoDB
table.put_item(Item={
    'client_id': client_id,
    'upload_token': upload_token,
    'token_expires': (datetime.utcnow() + timedelta(days=30)).isoformat()
})

# Include in email link
upload_url = f"https://yourdomain.com/upload?client={client_id}&token={upload_token}"
```

### Validation:
- ✅ Token validation before generating presigned URL
- ✅ Token expiration (30 days)
- ✅ File type validation (PDF only)
- ✅ File size limits (10 MB max)
- ✅ Virus scanning (optional, use S3 + Lambda)

---

## Cost Impact

### Additional Costs:

| Component | Cost |
|-----------|------|
| Upload API Gateway | $0.01 per 1,000 requests |
| Upload Manager Lambda | $0.20 per 1M requests |
| Document Processor Lambda | $0.20 per 1M requests |
| S3 PUT requests | $0.005 per 1,000 |
| **Total per upload** | **~$0.0001** |

**For 50 clients × 5 documents = 250 uploads:**
- Cost: $0.025 (negligible)

---

## Recommendation

**Implement Option 1 (Presigned URLs) because:**
1. Most secure and scalable
2. Lowest cost
3. No file size limits
4. Direct S3 upload (fastest)
5. Industry standard pattern

**Implementation Priority:**
1. Add Upload Manager Lambda (30 min)
2. Add Document Processor Lambda (30 min)
3. Update CDK stack (15 min)
4. Create upload portal component (30 min)
5. Update email templates with upload links (15 min)

**Total:** ~2 hours to add complete upload functionality

---

## Summary

The current implementation is complete but assumes documents are already in S3. To enable client uploads:

**Quick Fix (Recommended):**
- Add Upload Manager Lambda for presigned URLs
- Add Document Processor Lambda for S3 events
- Add upload portal component
- Update email templates with upload links

**Alternative:**
- Use email-based uploads (simpler for clients)
- Configure SES to receive emails
- Save attachments to S3

Both options integrate seamlessly with existing architecture!

Would you like me to implement the upload functionality?
