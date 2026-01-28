# Implementation Plan: SMS Notifications via Amazon SNS

## Overview

Add SMS notification capability alongside email reminders using Amazon SNS to improve client engagement. Clients can opt-in to receive SMS notifications for upload link reminders and document status updates.

## Goals

1. **Dual-channel communication**: Email + SMS for better reach
2. **Opt-in based**: Clients choose to receive SMS
3. **Cost tracking**: Track SMS costs separately for billing
4. **Flexible**: Send SMS only, email only, or both
5. **Compliant**: Follow SMS best practices and regulations

## Current State Analysis

### Email Implementation
- Uses AWS SES for email delivery
- Sends upload links, reminders, and status updates
- Tracks email sending in usage table
- Cost: $0.0001 per email

### What Needs to Change
1. Add phone number field to client records
2. Add SMS preference flag
3. Integrate Amazon SNS for SMS
4. Update all notification functions to support SMS
5. Add SMS cost tracking
6. Update UI to collect phone numbers and preferences

## Implementation Plan

### Phase 1: Database Schema Updates

**Clients Table - New Fields**:
```python
{
  'client_id': 'Smith_abc123',
  'phone': '+12065551234',  # E.164 format
  'sms_enabled': True,       # Opt-in flag
  'notification_preferences': {
    'email': True,           # Default: true
    'sms': True,             # Default: false (opt-in)
    'upload_link': ['email', 'sms'],
    'reminders': ['email', 'sms'],
    'status_updates': ['email']
  }
}
```

### Phase 2: Backend - SNS Integration

#### 2.1 Create SNS Helper Module
**File**: `gateway/layers/common/python/sns_utils.py`

```python
import boto3
import logging
from typing import Optional

sns = boto3.client('sns')
logger = logging.getLogger()

def send_sms(
    phone_number: str,
    message: str,
    sender_id: Optional[str] = None
) -> str:
    """
    Send SMS via Amazon SNS.
    
    Args:
        phone_number: E.164 format (+12065551234)
        message: SMS text (max 160 chars for single message)
        sender_id: Optional sender ID (11 chars max)
    
    Returns:
        SNS message ID
    """
    params = {
        'PhoneNumber': phone_number,
        'Message': message,
        'MessageAttributes': {
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'  # Higher priority
            }
        }
    }
    
    if sender_id:
        params['MessageAttributes']['AWS.SNS.SMS.SenderID'] = {
            'DataType': 'String',
            'StringValue': sender_id[:11]  # Max 11 chars
        }
    
    response = sns.publish(**params)
    return response['MessageId']
```

#### 2.2 Update send_upload_link Lambda
**File**: `gateway/tools/send_upload_link/send_upload_link_lambda.py`

Add SMS support:
```python
def create_sms_body(client_name: str, upload_url: str, days_valid: int) -> str:
    """Create SMS message for upload link (160 chars max)."""
    # Use URL shortener or keep concise
    return f"Hi {client_name}, upload your tax docs here: {upload_url} (valid {days_valid}d)"

def send_notifications(
    client_info: Dict[str, Any],
    upload_url: str,
    days_valid: int,
    custom_message: Optional[str] = None
) -> Dict[str, str]:
    """
    Send notifications via email and/or SMS based on preferences.
    
    Returns:
        Dict with message IDs: {'email': 'msg-id', 'sms': 'msg-id'}
    """
    results = {}
    prefs = client_info.get('notification_preferences', {})
    
    # Send email if enabled
    if prefs.get('email', True):
        email_id = send_email_via_ses(...)
        results['email'] = email_id
    
    # Send SMS if enabled and phone available
    if prefs.get('sms', False) and client_info.get('phone'):
        sms_body = create_sms_body(...)
        sms_id = send_sms(client_info['phone'], sms_body)
        results['sms'] = sms_id
        
        # Track SMS usage
        track_usage(
            accountant_id=client_info['accountant_id'],
            operation='send_upload_link',
            resource_type='sms_sent',
            quantity=1
        )
    
    return results
```

#### 2.3 Update batch_operations Lambda
Similar changes to support SMS in bulk operations.

#### 2.4 Update Usage Tracking
Add SMS pricing:
```python
pricing = {
    'email_sent': 0.0001,
    'sms_sent': 0.00645,  # US SMS cost via SNS
    'agent_invocation': 0.003,
    'gateway_call': 0.0001,
}
```

### Phase 3: Frontend Updates

#### 3.1 Update NewClientIntake Component
**File**: `frontend/src/components/tax/NewClientIntake.tsx`

Add fields:
```typescript
- Phone number input (with validation)
- SMS opt-in checkbox
- Notification preferences section
```

#### 3.2 Update SendUploadLinkForm Component
**File**: `frontend/src/components/tax/SendUploadLinkForm.tsx`

Add:
```typescript
- Display client phone number if available
- Show SMS status (enabled/disabled)
- Option to send via email only, SMS only, or both
```

#### 3.3 Update ClientDetailView Component
**File**: `frontend/src/components/tax/ClientDetailView.tsx`

Add:
```typescript
- Phone number display/edit
- SMS preferences toggle
- Notification history (email + SMS)
```

### Phase 4: CDK Infrastructure

#### 4.1 Update Lambda IAM Permissions
**File**: `infra-cdk/lib/tax-agent-backend-stack.ts`

Add SNS permissions:
```typescript
// Add to Lambda execution roles
new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    'sns:Publish',
    'sns:SetSMSAttributes',
    'sns:GetSMSAttributes'
  ],
  resources: ['*']
})
```

#### 4.2 Update Lambda Environment Variables
Add:
```typescript
SMS_SENDER_ID: 'TaxAgent',  // Optional, 11 chars max
SMS_ENABLED: 'true'
```

#### 4.3 SNS Spending Limits (Optional)
Set monthly SMS spending limit via CDK or Console:
```typescript
// Via AWS Console: SNS → Text messaging (SMS) → Spending limit
// Default: $1.00/month
// Recommended: $10-50/month depending on client count
```

### Phase 5: Tool Spec Updates

#### 5.1 Update send_upload_link tool spec
**File**: `gateway/tools/send_upload_link/tool_spec.json`

Add parameters:
```json
{
  "send_via": {
    "type": "string",
    "enum": ["email", "sms", "both"],
    "default": "both",
    "description": "Notification channel(s) to use"
  }
}
```

### Phase 6: Testing & Validation

#### 6.1 Phone Number Validation
- E.164 format validation
- Country code required (+1 for US)
- Regex: `^\+[1-9]\d{1,14}$`

#### 6.2 SMS Message Length
- Single SMS: 160 characters
- Multi-part: 153 chars per segment
- Keep messages concise

#### 6.3 Cost Monitoring
- Track SMS costs per accountant
- Alert if spending exceeds threshold
- Show SMS usage in billing dashboard

## Cost Analysis

### SMS Pricing (via Amazon SNS)
- **US**: $0.00645 per SMS
- **Canada**: $0.00645 per SMS
- **International**: Varies by country ($0.02-0.50)

### Cost Comparison
| Notification Type | Cost per Send | 100 Clients | 1000 Clients |
|-------------------|---------------|-------------|--------------|
| Email only        | $0.0001       | $0.01       | $0.10        |
| SMS only          | $0.00645      | $0.65       | $6.45        |
| Email + SMS       | $0.00655      | $0.66       | $6.55        |

### Monthly Cost Estimate
Assuming 3 notifications per client per month:
- Email only: $0.30 for 1000 clients
- SMS only: $19.35 for 1000 clients
- Email + SMS: $19.65 for 1000 clients

## Implementation Phases

### Phase 1: Core SMS Infrastructure (2-3 hours)
- [ ] Add phone field to client schema
- [ ] Create SNS helper module
- [ ] Update send_upload_link Lambda
- [ ] Add SMS cost tracking
- [ ] Update IAM permissions

### Phase 2: Frontend Integration (2 hours)
- [ ] Add phone input to NewClientIntake
- [ ] Add SMS preferences to SendUploadLinkForm
- [ ] Update ClientDetailView with phone/SMS settings

### Phase 3: Bulk Operations (1 hour)
- [ ] Update batch_operations Lambda
- [ ] Add SMS support to reminders
- [ ] Test bulk SMS sending

### Phase 4: Testing & Documentation (1 hour)
- [ ] Test SMS delivery
- [ ] Verify cost tracking
- [ ] Update documentation
- [ ] Create user guide

**Total Estimated Time**: 6-7 hours

## Deployment Strategy

### Step 1: Deploy Backend
```bash
cd infra-cdk
cdk deploy tax-agent
```

### Step 2: Test SMS Sending
```bash
# Test with your own phone number first
python3 scripts/test-sms-notification.py
```

### Step 3: Deploy Frontend
```bash
python3 scripts/deploy-frontend.py
```

### Step 4: Gradual Rollout
1. Enable for test clients only
2. Monitor costs and delivery rates
3. Enable for all clients
4. Promote SMS opt-in to clients

## Compliance & Best Practices

### SMS Regulations
1. **Opt-in Required**: Clients must explicitly consent
2. **Opt-out Support**: Include "Reply STOP to unsubscribe"
3. **Identification**: Clearly identify sender
4. **Timing**: Avoid sending between 9 PM - 8 AM local time
5. **Content**: Keep messages relevant and concise

### Message Templates
```
Upload Link:
"Hi {name}, upload your tax docs: {url} (valid {days}d). Reply STOP to opt out."

Reminder:
"Reminder: We still need your {doc_type} for 2026 taxes. Upload at {url}. Reply STOP to opt out."

Status Update:
"Great! We received your {doc_type}. {remaining} documents remaining. Reply STOP to opt out."
```

### Error Handling
- Invalid phone numbers: Log and notify accountant
- Delivery failures: Fallback to email
- Opt-out requests: Update preferences automatically
- Cost limits: Alert when approaching spending limit

## Success Metrics

### Engagement Metrics
- SMS delivery rate (target: >95%)
- SMS open rate (target: >90%)
- Response time improvement (target: 50% faster)
- Client satisfaction (survey)

### Cost Metrics
- Average SMS cost per client
- SMS vs email effectiveness
- ROI on SMS notifications

### Technical Metrics
- SMS delivery latency
- Error rate
- Opt-out rate

## Rollback Plan

If issues arise:
1. Disable SMS via environment variable
2. Revert to email-only notifications
3. Fix issues in development
4. Redeploy with fixes

## Future Enhancements

1. **Two-way SMS**: Receive client responses
2. **SMS Templates**: Customizable per accountant
3. **Scheduling**: Send at optimal times
4. **A/B Testing**: Test message variations
5. **Rich Messaging**: MMS with images/PDFs
6. **WhatsApp Integration**: Alternative to SMS

## Configuration (Approved)

1. **Sender ID**: "YourFirm" (11 chars max)
2. **Default Behavior**: Opt-in (clients must explicitly enable SMS)
3. **Spending Limit**: $10/month (~1,550 SMS messages)
4. **Countries**: US only (+1 country code)
5. **Timing Restrictions**: 8 AM - 8 PM local time only
6. **Testing**: Complete all code first, then test
7. **Deployment**: Backend first, test, then frontend
8. **Phone Collection**: Edit form + gradual + bulk import
9. **Default Send**: Both (email + SMS) if SMS enabled

## Next Steps

Please review this plan and provide:
1. Approval to proceed
2. Answers to the questions above
3. Any modifications or additional requirements

Once approved, I'll begin implementation starting with Phase 1.
