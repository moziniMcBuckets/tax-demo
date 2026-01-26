# Document Download Feature - Implementation Plan

## Overview
Add ability for accountants to download client documents from the dashboard and detail view.

---

## Architecture

### Flow
```
Dashboard/Detail View → API Gateway → Lambda → S3 Presigned URL → Browser Download
```

### Components

1. **API Gateway Endpoint:** `GET /documents/{client_id}/{document_type}`
2. **Lambda Function:** Reuse existing `upload_manager` or create new `document_downloader`
3. **S3 Presigned URL:** GET operation (15-minute expiration)
4. **Frontend:** Download buttons in Client Detail View

---

## Implementation Steps

### Step 1: Update Upload Manager Lambda (10 min)
Add download functionality to existing Lambda to handle both upload and download.

**File:** `gateway/tools/upload_manager/upload_manager_lambda.py`

**Add function:**
```python
def generate_download_url(client_id: str, client_name: str, document_type: str, tax_year: int) -> str:
    # Find file in S3
    # Generate presigned GET URL
    # Return URL
```

### Step 2: Add API Gateway Endpoint (10 min)
**File:** `infra-cdk/lib/backend-stack.ts`

**Add to createFeedbackApi:**
```typescript
// GET /documents
const documentsResource = api.root.addResource("documents")
const clientIdResource = documentsResource.addResource("{clientId}")
const docTypeResource = clientIdResource.addResource("{documentType}")

docTypeResource.addMethod("GET", 
  new apigateway.LambdaIntegration(uploadManagerLambda),
  {
    authorizer,
    authorizationType: apigateway.AuthorizationType.COGNITO,
  }
)
```

### Step 3: Update Frontend (20 min)
**File:** `frontend/src/components/tax/ClientDetailView.tsx`

**Add download button:**
```typescript
const handleDownload = async (documentType: string) => {
  const response = await fetch(
    `${apiUrl}documents/${clientId}/${documentType}`,
    { headers: { Authorization: `Bearer ${idToken}` } }
  );
  const { download_url } = await response.json();
  window.open(download_url, '_blank');
};
```

### Step 4: Deploy (5 min)
```bash
cd infra-cdk
cdk deploy tax-agent
python3 scripts/deploy-frontend.py
```

---

## Total Time: 45 minutes

## Testing
1. View client detail
2. Click download button
3. File downloads to browser
4. Verify correct file

---

**Status:** Ready to implement
