# Onboarding Guide - Tax Document Agent

## Welcome!

This guide will help you get started with the Tax Document Collection Agent. Follow these steps to go from deployment to your first client.

---

## Step 1: Deploy the System (20 minutes)

Follow the complete deployment guide in `DEPLOYMENT.md`.

**Quick checklist:**
- [ ] AWS account configured
- [ ] Prerequisites installed
- [ ] CDK deployed
- [ ] Frontend deployed
- [ ] SES email verified
- [ ] Cognito user created

**Result:** System is live and accessible

---

## Step 2: Understand the System (10 minutes)

### What You Have:

**Frontend (3 tabs):**
1. **Chat** - Talk to AI agent with natural language
2. **Dashboard** - Visual overview with real-time data, filters, and search
3. **Upload** - Client document portal (accessed via secure link)

**Backend (7 Gateway tools + 1 processor):**
1. Document Checker - Scans S3 for uploaded documents
2. Email Sender - Sends reminders via SES
3. Status Tracker - Shows client overview
4. Escalation Manager - Flags urgent cases
5. Requirement Manager - Manages doc lists
6. Upload Manager - Creates presigned S3 URLs
7. Send Upload Link - Generates and emails upload links
8. Document Processor - S3-triggered status updates

### How It Works:

```
Client needs documents
    ↓
Agent tracks status
    ↓
Sends automatic reminders (Day 3, 10, 24)
    ↓
Client uploads via secure link
    ↓
Agent detects upload
    ↓
Updates status automatically
    ↓
Notifies accountant when complete
```

---

## Step 3: Test with Sample Data (15 minutes)

### 3.1 Seed Test Data

```bash
python3 scripts/seed-tax-test-data.py
```

**Creates:**
- 5 test clients (various statuses)
- Document requirements
- Follow-up history
- Accountant settings

### 3.2 Test Gateway Tools

```bash
python3 scripts/test-all-gateway-tools.py
```

**Verifies:**
- All 7 Gateway tools respond correctly
- DynamoDB access works
- S3 access works
- Email sending configured
- No errors

### 3.3 Test Upload Link Feature

```bash
python3 scripts/test-send-upload-link.py --client-id client_001
```

**Verifies:**
- Token generation works
- Email delivery succeeds
- Upload portal accessible
- S3 presigned URLs generated

### 3.3 Test Frontend

1. Open your Amplify URL
2. Log in with Cognito user
3. Try these queries:

**First query:**
```
Show me all my clients
```
**Response:** "I need your accountant ID"

**Second query:**
```
acc_test_001
```
**Response:** Shows 5 clients with statuses

**Third query:**
```
Send Mohamed his upload link
```
**Response:** "Upload link sent to mohamed@example.com! Valid for 30 days."

**Fourth query:**
```
Which clients are at risk?
```
**Response:** Lists at-risk clients

**Fifth query:**
```
What documents has Mohamed submitted?
```
**Response:** Shows uploaded documents with dates

---

## Step 4: Add Your First Real Client (10 minutes)

### 4.1 Create Client Record

**Via DynamoDB Console:**
1. Go to DynamoDB → Tables → `<stack>-clients`
2. Create item:
```json
{
  "client_id": "client_001",
  "client_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-0123",
  "accountant_id": "your_accountant_id",
  "status": "incomplete",
  "created_at": "2026-01-25T00:00:00Z"
}
```

### 4.2 Set Document Requirements

Ask the agent:
```
Add standard requirements for client_001 for tax year 2024
```

Or use the requirement manager tool directly.

### 4.3 Generate Upload Token

```bash
python3 scripts/generate-upload-token.py --client-id client_001
```

**Output:** Secure upload URL

### 4.4 Send to Client

Email the upload URL to your client with instructions.

---

## Step 5: Monitor and Manage (Ongoing)

### Daily Tasks:

**Morning (5 minutes):**
1. Open dashboard
2. Check for escalated clients (red)
3. Review at-risk clients (orange)

**Ask agent:**
```
What needs my attention today?
```

### Weekly Tasks:

**Review Progress (10 minutes):**
```
Give me a summary of this week's progress
```

**Check Costs:**
- CloudWatch dashboard
- AWS Cost Explorer

### As Needed:

**Send Reminders:**
```
Send reminders to all incomplete clients
```

**Check Specific Client:**
```
What's the status of Jane Doe?
```

**Escalate:**
```
Escalate John Smith
```

---

## Step 6: Customize (Optional)

### Email Templates

Update in DynamoDB `<stack>-settings` table:
```json
{
  "accountant_id": "your_id",
  "settings_type": "email_templates",
  "templates": {
    "reminder_1": {
      "subject": "Your custom subject",
      "body": "Your custom message"
    }
  }
}
```

### Agent Behavior

Edit `patterns/strands-single-agent/tax_document_agent.py`:
- Update system prompt
- Adjust model temperature
- Add custom logic

Redeploy:
```bash
cd infra-cdk
cdk deploy tax-agent
```

### Frontend Branding

Edit `frontend/src/app/layout.tsx`:
- Update title
- Add logo
- Change colors

Redeploy:
```bash
python3 scripts/deploy-frontend.py
```

---

## Best Practices

### For Accountants:

1. **Check dashboard daily** during tax season
2. **Respond to escalations** within 24 hours
3. **Keep client emails updated** in DynamoDB
4. **Monitor email delivery** rates
5. **Review costs** weekly

### For System Admins:

1. **Monitor CloudWatch** for errors
2. **Check Lambda logs** if issues arise
3. **Keep SES in good standing** (low bounce rate)
4. **Backup DynamoDB** regularly
5. **Test after any changes**

### For Clients:

1. **Upload documents promptly** when reminded
2. **Use correct document types** when uploading
3. **Contact accountant** if upload issues
4. **Keep email address current**

---

## Success Metrics

### Week 1:
- [ ] All test clients working
- [ ] Emails sending successfully
- [ ] Dashboard showing correct data
- [ ] No errors in CloudWatch

### Month 1:
- [ ] 10+ real clients onboarded
- [ ] 90%+ email delivery rate
- [ ] < $10 AWS costs
- [ ] Positive feedback from accountants

### Tax Season:
- [ ] 50+ clients managed
- [ ] 95%+ on-time submission rate
- [ ] 8 hours/week time saved
- [ ] Zero missed deadlines

---

## Support Resources

- **Documentation:** `docs/` folder
- **Code:** `gateway/tools/` and `patterns/`
- **Scripts:** `scripts/` folder
- **AWS Console:** CloudWatch, Lambda, DynamoDB

---

## Quick Reference

### Important Commands:

```bash
# Deploy
cdk deploy --all

# Test
python3 scripts/test-all-gateway-tools.py

# Seed data
python3 scripts/seed-tax-test-data.py

# Generate upload token
python3 scripts/generate-upload-token.py --client-id <id>

# Check logs
aws logs tail /aws/lambda/<function-name> --follow

# Verify email
aws ses verify-email-identity --email-address <email>
```

### Important URLs:

- Frontend: Check Amplify outputs
- AWS Console: https://console.aws.amazon.com
- Cognito: https://console.aws.amazon.com/cognito
- CloudWatch: https://console.aws.amazon.com/cloudwatch

---

**Need Help?** Check `DEPLOYMENT.md` and `ARCHITECTURE.md` for detailed information.
