# SMS Notification Implementation Status

## Configuration (Approved)
- Sender ID: "YourFirm"
- Default: Opt-in only
- Budget: $10/month (~1,550 SMS)
- Countries: US only
- Hours: 8 AM - 8 PM local time

## Completed So Far

### 1. SNS Helper Module ✅
**File**: `gateway/layers/common/python/sns_utils.py`
- Phone validation (E.164 format, US only)
- Time window checking (8 AM - 8 PM)
- SMS sending with error handling
- Message truncation (160 char limit)
- Template functions for different message types
- Spending limit management

### 2. Partial Lambda Updates ✅
**File**: `gateway/tools/send_upload_link/send_upload_link_lambda.py`
- Added SNS client initialization
- Added SMS pricing to usage tracking
- Added SMS_SENDER_ID environment variable
- Added SMS sending functions
- Updated handler to support `send_via` parameter ('email', 'sms', 'both')
- Multi-channel notification support

## Remaining Work

### Phase 1: Complete Backend (2-3 hours)
- [ ] Update tool spec with `send_via` parameter
- [ ] Update batch_operations Lambda for SMS support
- [ ] Add phone/sms_enabled fields to client_management Lambda
- [ ] Test Python code syntax

### Phase 2: CDK Infrastructure (1 hour)
- [ ] Add SNS permissions to Lambda IAM roles
- [ ] Add SMS_SENDER_ID environment variable to Lambdas
- [ ] Set SNS spending limit ($10/month)
- [ ] Update Lambda layer to include sns_utils.py

### Phase 3: Frontend (2 hours)
- [ ] Add phone field to NewClientIntake component
- [ ] Add sms_enabled checkbox
- [ ] Update SendUploadLinkForm with SMS options
- [ ] Update ClientDetailView with phone/SMS settings
- [ ] Add phone validation on frontend

### Phase 4: Testing & Documentation (1 hour)
- [ ] Test SMS sending with real phone number
- [ ] Verify cost tracking
- [ ] Update REPLICATION_GUIDE.md
- [ ] Create SMS feature documentation
- [ ] Update SAMPLE_QUERIES.md

## Database Schema Changes Needed

```python
# Clients Table - New Fields
{
  'phone': '+12065551234',      # E.164 format, optional
  'sms_enabled': False,          # Default: false (opt-in)
  'notification_preferences': {  # Optional
    'email': True,
    'sms': False,
    'channels': ['email']        # Default: email only
  }
}
```

## Files Modified So Far
1. ✅ `gateway/layers/common/python/sns_utils.py` (NEW)
2. ✅ `gateway/tools/send_upload_link/send_upload_link_lambda.py` (UPDATED)

## Files Still To Modify
1. `gateway/tools/send_upload_link/tool_spec.json`
2. `infra-cdk/lambdas/batch_operations/index.py`
3. `infra-cdk/lambdas/client_management/index.py`
4. `infra-cdk/lib/tax-agent-backend-stack.ts`
5. `frontend/src/components/tax/NewClientIntake.tsx`
6. `frontend/src/components/tax/SendUploadLinkForm.tsx`
7. `frontend/src/components/tax/ClientDetailView.tsx`
8. `docs/REPLICATION_GUIDE.md`
9. `docs/SAMPLE_QUERIES.md`

## Estimated Time Remaining
- Backend completion: 2-3 hours
- CDK infrastructure: 1 hour
- Frontend: 2 hours
- Testing/docs: 1 hour
**Total: 6-7 hours**

## Questions Before Continuing

1. **Approve to continue?** Should I proceed with the remaining implementation?

2. **Testing approach**: Do you want me to:
   - Complete all code first, then test?
   - Test incrementally (backend, then frontend)?

3. **Deployment strategy**: Should I:
   - Complete everything, then deploy once?
   - Deploy backend first, test, then deploy frontend?

4. **Phone number collection**: For existing clients without phone numbers:
   - Add phone field to client edit form?
   - Bulk import via CSV?
   - Collect gradually as needed?

5. **Default behavior**: When sending upload links:
   - Default to email only (safer)?
   - Default to both if SMS enabled (more engagement)?
   - Let accountant choose each time?

Please review and let me know if you want me to:
- Continue with the implementation as planned
- Make any changes to the approach
- Pause and discuss any concerns
