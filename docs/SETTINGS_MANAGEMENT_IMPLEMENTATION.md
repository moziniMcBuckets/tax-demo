# Settings Management Implementation Plan

## Overview
Implement accountant settings and preferences for customization and personalization.

---

## Architecture

```
Settings UI → Settings API → DynamoDB (settings table) → Used by all Lambdas
```

---

## Settings Categories

### 1. Email Templates
**Customize reminder emails:**
```json
{
  "accountant_id": "user-123",
  "settings_type": "email_templates",
  "templates": {
    "reminder_1": {
      "subject": "Friendly Reminder: Tax Documents Needed",
      "body": "Hi {client_name},\n\nJust a friendly reminder..."
    },
    "reminder_2": {
      "subject": "Important: Tax Documents Still Needed",
      "body": "Hi {client_name},\n\nThis is my second request..."
    },
    "upload_link": {
      "subject": "Secure Upload Link for Your Tax Documents",
      "body": "Hi {client_name},\n\nPlease use this link..."
    }
  }
}
```

### 2. Contact Information
**Accountant details for emails:**
```json
{
  "accountant_id": "user-123",
  "settings_type": "contact_info",
  "firm_name": "Johnson Tax Services",
  "accountant_name": "Sarah Johnson",
  "phone": "+1-555-0100",
  "email": "sarah@johnsontax.com",
  "address": "123 Main St, City, State 12345",
  "website": "https://johnsontax.com"
}
```

### 3. Preferences
**Workflow preferences:**
```json
{
  "accountant_id": "user-123",
  "settings_type": "preferences",
  "escalation_threshold": 3,
  "reminder_schedule_days": [3, 7, 14],
  "auto_send_upload_links": true,
  "notification_email": "sarah@johnsontax.com",
  "timezone": "America/Los_Angeles",
  "business_hours": {
    "start": "09:00",
    "end": "17:00"
  }
}
```

### 4. Branding
**Custom branding:**
```json
{
  "accountant_id": "user-123",
  "settings_type": "branding",
  "logo_url": "https://...",
  "primary_color": "#1E40AF",
  "email_signature": "Best regards,\nSarah Johnson\nJohnson Tax Services"
}
```

---

## Implementation

### Phase 1: Settings UI (3 hours)

**1.1 Create Settings Page:**
```typescript
// frontend/src/components/settings/SettingsPage.tsx

export function SettingsPage() {
  const [settings, setSettings] = useState(null);
  
  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Account Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="profile">
            <TabsList>
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="email">Email Templates</TabsTrigger>
              <TabsTrigger value="preferences">Preferences</TabsTrigger>
              <TabsTrigger value="branding">Branding</TabsTrigger>
            </TabsList>
            
            <TabsContent value="profile">
              <ProfileSettings />
            </TabsContent>
            
            <TabsContent value="email">
              <EmailTemplateEditor />
            </TabsContent>
            
            <TabsContent value="preferences">
              <PreferencesForm />
            </TabsContent>
            
            <TabsContent value="branding">
              <BrandingSettings />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
```

**1.2 Email Template Editor:**
```typescript
function EmailTemplateEditor() {
  const [templates, setTemplates] = useState({});
  const [editing, setEditing] = useState(null);
  
  return (
    <div className="space-y-4">
      {Object.entries(templates).map(([key, template]) => (
        <Card key={key}>
          <CardHeader>
            <CardTitle>{key.replace('_', ' ').toUpperCase()}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Input
                label="Subject"
                value={template.subject}
                onChange={(e) => updateTemplate(key, 'subject', e.target.value)}
              />
              <textarea
                label="Body"
                value={template.body}
                onChange={(e) => updateTemplate(key, 'body', e.target.value)}
                rows={10}
              />
              <p className="text-xs text-gray-500">
                Available variables: {'{client_name}'}, {'{missing_documents}'}, {'{deadline}'}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
      
      <Button onClick={saveTemplates}>Save Templates</Button>
    </div>
  );
}
```

### Phase 2: Settings API (1 hour)

**2.1 Create Settings Lambda:**
```python
# infra-cdk/lambdas/settings/index.py

def get_settings(accountant_id: str, settings_type: str = None):
    """Get accountant settings."""
    table = dynamodb.Table('tax-agent-settings')
    
    if settings_type:
        response = table.get_item(
            Key={'accountant_id': accountant_id, 'settings_type': settings_type}
        )
        return response.get('Item', {})
    else:
        response = table.query(
            KeyConditionExpression='accountant_id = :aid',
            ExpressionAttributeValues={':aid': accountant_id}
        )
        return response.get('Items', [])

def update_settings(accountant_id: str, settings_type: str, settings_data: dict):
    """Update accountant settings."""
    table = dynamodb.Table('tax-agent-settings')
    
    table.put_item(Item={
        'accountant_id': accountant_id,
        'settings_type': settings_type,
        **settings_data,
        'updated_at': datetime.utcnow().isoformat()
    })
```

**2.2 Add API Endpoints:**
```typescript
// GET /settings?type=email_templates
// POST /settings
// PUT /settings/{type}
// DELETE /settings/{type}
```

### Phase 3: Use Settings in Lambdas (2 hours)

**3.1 Email Sender:**
```python
# Get custom template if exists
settings_table = dynamodb.Table('tax-agent-settings')
response = settings_table.get_item(
    Key={'accountant_id': accountant_id, 'settings_type': 'email_templates'}
)

if 'Item' in response:
    custom_templates = response['Item'].get('templates', {})
    template = custom_templates.get(f'reminder_{followup_number}', default_template)
else:
    template = default_template
```

**3.2 Escalation Manager:**
```python
# Get custom thresholds
response = settings_table.get_item(
    Key={'accountant_id': accountant_id, 'settings_type': 'preferences'}
)

if 'Item' in response:
    escalation_threshold = response['Item'].get('escalation_threshold', 3)
else:
    escalation_threshold = 3  # Default
```

---

## Features

### Email Template Management:
- ✅ Edit reminder templates
- ✅ Preview before saving
- ✅ Use variables (client_name, etc.)
- ✅ Reset to defaults
- ✅ A/B test templates

### Profile Settings:
- ✅ Firm name and contact info
- ✅ Email signature
- ✅ Logo upload
- ✅ Timezone
- ✅ Business hours

### Preferences:
- ✅ Escalation rules
- ✅ Reminder schedule
- ✅ Auto-send upload links
- ✅ Notification preferences
- ✅ Default document requirements

### Branding:
- ✅ Custom colors
- ✅ Logo in emails
- ✅ Custom domain (future)
- ✅ White-label option

---

## Implementation Timeline

**Week 1: Core Settings**
- Settings UI with tabs
- Profile and contact info
- Save/load functionality

**Week 2: Email Templates**
- Template editor
- Preview functionality
- Variable substitution
- Integration with email sender

**Week 3: Preferences**
- Workflow preferences
- Escalation rules
- Notification settings
- Integration with all Lambdas

**Week 4: Branding**
- Logo upload to S3
- Color customization
- Email signature
- Apply to all communications

---

## Benefits

### For Accountants:
- 🎨 Personalize communication
- ⚙️ Customize workflows
- 🏢 Professional branding
- ⏰ Set own schedules

### For Clients:
- 📧 Consistent communication
- 🎯 Relevant messages
- 🏢 Professional appearance
- ⏰ Timely reminders

---

## Success Metrics

- ✅ 80%+ accountants customize settings
- ✅ Custom templates improve response rates
- ✅ Branding increases trust
- ✅ Preferences reduce manual work

---

**Status:** Implementation plan ready  
**Priority:** Medium (nice-to-have for beta)  
**Effort:** 1-2 weeks  
**Value:** Personalization, professional branding, workflow optimization
