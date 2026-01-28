# Moving from SES Sandbox to Production

## Overview
Plan for requesting and implementing SES production access for the tax demo application.

---

## Current State: SES Sandbox

### Limitations:
- ❌ Can only send TO verified email addresses
- ❌ Limited to 200 emails per 24 hours
- ❌ Can only send FROM verified addresses
- ❌ Not suitable for production/beta with real users

### What Works:
- ✅ Can send from `mhamuzn@amazon.com` (verified)
- ✅ Can send to verified addresses only
- ✅ Good for development and testing

---

## Production Access Benefits

### After Approval:
- ✅ Send to ANY email address (no verification needed)
- ✅ Higher sending limits (50,000 emails/day initially)
- ✅ Can request limit increases
- ✅ Better deliverability
- ✅ Access to dedicated IPs (optional)
- ✅ Reputation dashboard

---

## Request Process

### Step 1: Prepare Use Case Description

**What to include:**
```
Application: Tax Document Collection Agent
Purpose: Send automated reminders and upload links to tax clients
Expected Volume: 1,000-5,000 emails per month during tax season
Email Types:
- Document collection reminders
- Upload link notifications
- Status updates to accountants
- Escalation alerts

Compliance:
- All emails are transactional (not marketing)
- Recipients are existing clients with business relationship
- Unsubscribe not required (transactional)
- Bounce and complaint handling implemented

Email Content:
- Professional tax document requests
- Secure upload links
- Deadline reminders
- No spam or promotional content
```

### Step 2: Submit Request

**Via AWS Console:**
1. Go to: AWS Console → Amazon SES → Account Dashboard
2. Click "Request production access"
3. Fill out form:
   - **Mail type:** Transactional
   - **Website URL:** https://main.d3tseyzyms135a.amplifyapp.com
   - **Use case description:** [Use template above]
   - **Compliance:** Confirm you'll handle bounces/complaints
   - **Additional contacts:** Your email
4. Submit

**Via AWS CLI:**
```bash
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --website-url https://main.d3tseyzyms135a.amplifyapp.com \
  --use-case-description "Tax document collection system sending transactional emails to clients..." \
  --additional-contact-email-addresses mhamuzn@amazon.com
```

### Step 3: Wait for Approval

**Timeline:**
- Typical: 24 hours
- Can be: Up to 48 hours
- Rarely: Requires additional information

**What AWS Reviews:**
- Use case legitimacy
- Compliance with policies
- Bounce/complaint handling
- Email content quality

---

## Implementation After Approval

### Step 1: Verify Approval Status

```bash
aws sesv2 get-account --query 'ProductionAccessEnabled'
# Should return: true
```

### Step 2: Configure Bounce/Complaint Handling

**2.1 Create SNS Topics:**
```typescript
// In CDK
const bouncesTopic = new sns.Topic(this, 'SESBounces', {
  topicName: `${config.stack_name_base}-ses-bounces`
});

const complaintsTopic = new sns.Topic(this, 'SESComplaints', {
  topicName: `${config.stack_name_base}-ses-complaints`
});
```

**2.2 Configure SES Notifications:**
```bash
aws ses set-identity-notification-topic \
  --identity mhamuzn@amazon.com \
  --notification-type Bounce \
  --sns-topic arn:aws:sns:us-west-2:ACCOUNT:tax-agent-ses-bounces

aws ses set-identity-notification-topic \
  --identity mhamuzn@amazon.com \
  --notification-type Complaint \
  --sns-topic arn:aws:sns:us-west-2:ACCOUNT:tax-agent-ses-complaints
```

**2.3 Create Handler Lambda:**
```python
# infra-cdk/lambdas/ses_handler/index.py

def handle_bounce(message):
    """Handle bounced email."""
    # Extract email address
    bounce_email = message['bounce']['bouncedRecipients'][0]['emailAddress']
    
    # Update client record
    clients_table.update_item(
        Key={'client_id': client_id},
        UpdateExpression='SET email_bounced = :true, email_status = :status',
        ExpressionAttributeValues={
            ':true': True,
            ':status': 'bounced'
        }
    )
    
    # Notify accountant
    # Log for review

def handle_complaint(message):
    """Handle spam complaint."""
    # Mark email as complained
    # Stop sending to this address
    # Notify accountant
```

### Step 3: Implement Email Best Practices

**3.1 Add Unsubscribe (Optional for Transactional)**
```python
email_body += """

---
If you believe you received this email in error, please contact your accountant.
"""
```

**3.2 Monitor Reputation:**
```bash
# Check bounce rate (should be < 5%)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SES \
  --metric-name Reputation.BounceRate \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average
```

**3.3 Set Up Alerts:**
```typescript
// CloudWatch alarm for high bounce rate
new cloudwatch.Alarm(this, 'HighBounceRate', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/SES',
    metricName: 'Reputation.BounceRate',
    statistic: 'Average',
  }),
  threshold: 5,  // 5% bounce rate
  evaluationPeriods: 1,
  alarmDescription: 'SES bounce rate too high',
});
```

### Step 4: Test Production Access

```bash
# Send test email to unverified address
aws ses send-email \
  --from mhamuzn@amazon.com \
  --destination ToAddresses=test@example.com \
  --message Subject={Data="Test"},Body={Text={Data="Testing production access"}}

# Should succeed without verification
```

---

## Sending Limits

### Initial Production Limits:
- **Sending rate:** 14 emails/second
- **Daily quota:** 50,000 emails/day

### Request Increase (if needed):
```
AWS Console → SES → Account Dashboard → Sending Statistics → Request Increase

Justification:
- Tax season peak: 10,000 emails/day
- 500 clients × 3 reminders × 3 months
- Need buffer for growth
```

---

## Monitoring & Maintenance

### Daily Checks:
- Bounce rate < 5%
- Complaint rate < 0.1%
- Sending quota usage
- Reputation score

### Monthly Tasks:
- Review bounced emails
- Update invalid email addresses
- Check deliverability metrics
- Adjust sending patterns if needed

### Alerts to Set Up:
1. Bounce rate > 5%
2. Complaint rate > 0.1%
3. Sending quota > 80%
4. Reputation score drops

---

## Cost Impact

**Sandbox:** Free (within limits)

**Production:**
- First 1,000 emails/month: Free
- Next 9,000: $0.10 per 1,000 = $0.90
- Total for 10,000 emails: $0.90/month

**Negligible cost increase!**

---

## Timeline

**Day 1:** Submit production access request  
**Day 2-3:** AWS reviews and approves  
**Day 3:** Configure bounce/complaint handling  
**Day 4:** Test with real client emails  
**Day 5:** Launch beta with production SES  

**Total:** 5 days from request to beta launch

---

## Checklist

### Before Requesting:
- [ ] Verify sender email (mhamuzn@amazon.com) ✅
- [ ] Test email sending in sandbox ✅
- [ ] Prepare use case description
- [ ] Confirm compliance with SES policies

### After Approval:
- [ ] Verify production access enabled
- [ ] Configure bounce/complaint handling
- [ ] Set up monitoring and alerts
- [ ] Test with unverified email
- [ ] Update documentation

### For Beta Launch:
- [ ] Production access active
- [ ] Bounce handling implemented
- [ ] Monitoring in place
- [ ] Test emails sent successfully
- [ ] Ready for real users

---

## Troubleshooting

**Request Denied:**
- Review use case description
- Ensure compliance with policies
- Provide more details
- Resubmit with clarifications

**High Bounce Rate:**
- Validate email addresses before sending
- Remove invalid addresses
- Improve email content
- Check spam score

**Emails Going to Spam:**
- Set up SPF/DKIM/DMARC
- Improve email content
- Avoid spam trigger words
- Use consistent sender

---

**Status:** Plan ready  
**Action:** Submit production access request  
**Timeline:** 5 days to beta launch  
**Priority:** Critical for beta release
