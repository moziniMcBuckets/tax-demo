# Usage Tracking & Billing Implementation Plan

## Overview
Track all operations per accountant for accurate billing and cost allocation.

---

## Architecture

### DynamoDB Table: `usage_tracking`
**Schema:**
- Partition Key: `accountant_id` (String)
- Sort Key: `timestamp` (String) - ISO format
- Attributes:
  - `operation` - Type of operation (send_email, agent_invocation, etc.)
  - `resource_type` - What was used (email, sms, storage, etc.)
  - `quantity` - How many (1 email, 5 clients, 2.5 GB, etc.)
  - `estimated_cost` - Cost in USD
  - `metadata` - Additional context (client_id, document_type, etc.)

**GSI:** `month-index` on `accountant_id` + `month` for monthly aggregation

---

## Tracked Operations

| Operation | Resource Type | Unit Cost | Tracked In |
|-----------|---------------|-----------|------------|
| Agent invocation | agent_session | $0.003 | Runtime |
| Gateway tool call | gateway_call | $0.0001 | Gateway |
| Email sent | email | $0.0001 | Email sender Lambda |
| SMS sent | sms | $0.00645 | SMS Lambda (future) |
| Document stored | storage_gb | $0.023/GB/month | S3 |
| Client active | client_month | $0.10/month | Monthly job |
| API call | api_request | $0.0000035 | API Gateway |

---

## Implementation

### Step 1: Create Usage Table (CDK)
### Step 2: Add tracking to all Lambdas
### Step 3: Create billing calculation Lambda
### Step 4: Add usage dashboard for accountants
### Step 5: Export for invoicing

---

**Time:** 2-3 hours
**Status:** Ready to implement
