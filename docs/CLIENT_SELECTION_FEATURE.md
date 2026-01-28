# Client Selection with Personalized Reminder Timing

## Overview

The Client Selection feature provides a user-friendly interface for accountants to send upload links to clients with personalized reminder timing preferences. This feature replaces the need to use the chat interface for sending upload links, offering a more intuitive and configurable approach.

## Features

- **Client Dropdown**: Select from a list of all your clients
- **Link Validity**: Configure how long the upload link remains valid (1-90 days)
- **Custom Messages**: Add personalized messages to the email
- **Reminder Scheduling**: 
  - Default schedule: 7, 14, 21, 30 days
  - Custom per-client schedules
  - Stored in DynamoDB for future use

## User Interface

### Location
Navigate to the **"Upload Documents"** tab in the main application.

### Components

1. **Client Selection Dropdown**
   - Populated with all clients for the authenticated accountant
   - Shows client name and email
   - Refresh button to reload client list

2. **Link Configuration**
   - Days valid: 1-90 days (default: 30)
   - Custom message textarea (optional)

3. **Reminder Schedule**
   - Toggle between default and custom schedules
   - Default: 7, 14, 21, 30 days after upload link sent
   - Custom: Set individual timing for each reminder

4. **Send Button**
   - Validates all inputs
   - Shows success/error notifications
   - Clears form after successful send

## Technical Implementation

### Frontend

**Component**: `frontend/src/components/tax/SendUploadLinkForm.tsx`

Key features:
- Fetches clients from `/clients` API endpoint
- Validates input before submission
- Calls `/batch-operations` API with `send_upload_links` operation
- Handles success/error states with professional UI

### Backend

**Modified Files**:
1. `infra-cdk/lambdas/batch_operations/index.py`
   - Added `reminder_preferences` parameter support
   - Stores preferences in DynamoDB when sending links

2. `gateway/tools/send_upload_link/send_upload_link_lambda.py`
   - Updated to accept and store `reminder_preferences`
   - Maintains backward compatibility

3. `gateway/tools/send_upload_link/tool_spec.json`
   - Documented new `reminder_preferences` parameter

### Database Schema

**Clients Table - New Field**:
```python
{
  'client_id': 'Smith_abc123',
  'reminder_preferences': {  # Optional field
    'first_reminder_days': 7,
    'second_reminder_days': 14,
    'third_reminder_days': 21,
    'escalation_days': 30
  }
}
```

## API Integration

### Endpoint Used
`POST /batch-operations`

### Request Format
```json
{
  "operation": "send_upload_links",
  "client_ids": ["client_id_1"],
  "options": {
    "days_valid": 30,
    "custom_message": "Optional message",
    "reminder_preferences": {
      "first_reminder_days": 7,
      "second_reminder_days": 14,
      "third_reminder_days": 21,
      "escalation_days": 30
    }
  }
}
```

### Response Format
```json
{
  "success": true,
  "operation": "send_upload_links",
  "total": 1,
  "succeeded": 1,
  "failed": 0,
  "results": [
    {
      "client_id": "client_id_1",
      "client_name": "John Smith",
      "success": true,
      "message": "Upload link sent to john@example.com"
    }
  ]
}
```

## Usage Examples

### Example 1: Send with Default Preferences
1. Select client from dropdown
2. Leave reminder preferences unchecked
3. Click "Send Upload Link"
4. Client receives email with default reminder schedule

### Example 2: Send with Custom Preferences
1. Select client from dropdown
2. Check "Customize for this client"
3. Set custom days: 5, 10, 15, 20
4. Add custom message
5. Click "Send Upload Link"
6. Preferences stored in DynamoDB for this client

### Example 3: Bulk Send (via Dashboard)
1. Go to Dashboard tab
2. Select multiple clients (checkboxes)
3. Click "Send Upload Links"
4. All selected clients receive links with default preferences

## Agent Integration

The AI agent can still send upload links via chat commands:

```
You: "Send Mohamed his upload link"
Agent: "Upload link sent to mohamed@example.com! Valid for 30 days."
```

Agent-sent links use default reminder preferences unless specified in the command.

## Testing

### Manual Testing Steps

1. **Test Client Selection**
   - Verify dropdown loads all clients
   - Verify refresh button works
   - Verify client details display correctly

2. **Test Default Preferences**
   - Send link without customization
   - Check DynamoDB: no `reminder_preferences` field
   - Verify email received

3. **Test Custom Preferences**
   - Enable custom preferences
   - Set custom values
   - Send link
   - Check DynamoDB: `reminder_preferences` field present
   - Verify values match input

4. **Test Upload Portal**
   - Copy link from email
   - Open in incognito browser
   - Verify upload works

5. **Test Agent Integration**
   - Use chat to send upload link
   - Verify still works
   - Check uses default preferences

### Verification Queries

```bash
# Check client record in DynamoDB
aws dynamodb get-item \
  --table-name <stack-name>-clients \
  --key '{"client_id":{"S":"<client-id>"}}' \
  --query 'Item.reminder_preferences'

# Check Lambda logs
aws logs tail /aws/lambda/<stack-name>-batch-operations --follow
```

## Troubleshooting

### Issue: Client dropdown is empty
**Solution**: 
- Check that clients exist in DynamoDB
- Verify JWT token is valid
- Check browser console for API errors

### Issue: Upload link not received
**Solution**:
- Verify SES email is verified
- Check CloudWatch logs for errors
- Verify client has valid email address

### Issue: Preferences not saving
**Solution**:
- Check DynamoDB permissions
- Verify Lambda has write access to clients table
- Check CloudWatch logs for errors

## Future Enhancements

1. **Reminder Preference Management**
   - View/edit preferences in ClientDetailView
   - Bulk update preferences for multiple clients

2. **Automated Reminders**
   - Schedule reminders based on stored preferences
   - EventBridge rules to trigger reminders

3. **Reminder History**
   - Track when reminders were sent
   - Show reminder history in client detail view

4. **Email Templates**
   - Customizable email templates per accountant
   - Template variables for personalization

## Related Documentation

- [Deployment Guide](DEPLOYMENT.md)
- [Replication Guide](REPLICATION_GUIDE.md)
- [Gateway Documentation](GATEWAY.md)
- [Sample Queries](SAMPLE_QUERIES.md)
