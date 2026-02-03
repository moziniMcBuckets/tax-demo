# Lead Response Tool

**Agent:** Lead Response Agent  
**Purpose:** Monitor inquiries, qualify leads, send responses  
**Pattern:** AgentCore Gateway tool

---

## Tools in This Package

### 1. monitor_email
- **Purpose:** Monitor Gmail/Outlook for new inquiries
- **Trigger:** Continuous (webhook or polling)
- **Inputs:** None
- **Outputs:** Email details (from, subject, body, timestamp)

### 2. monitor_sms
- **Purpose:** Receive SMS inquiries via Twilio
- **Trigger:** Twilio webhook
- **Inputs:** SMS data from Twilio
- **Outputs:** SMS details (from, body, timestamp)

### 3. monitor_web_form
- **Purpose:** Receive web form submissions
- **Trigger:** Website form webhook
- **Inputs:** Form data
- **Outputs:** Lead details (name, email, phone, message)

### 4. qualify_lead
- **Purpose:** Score and qualify leads
- **Inputs:** Lead details (service, urgency, budget, location)
- **Outputs:** Qualification score (1-10), qualified (yes/no), reason

### 5. store_lead
- **Purpose:** Store lead in DynamoDB
- **Inputs:** Lead details, qualification score
- **Outputs:** lead_id

### 6. send_response
- **Purpose:** Send response to lead via email or SMS
- **Inputs:** Lead contact info, message
- **Outputs:** Sent status

---

## Files to Create

- `lead_response_lambda.py` - Main Lambda handler
- `requirements.txt` - Python dependencies
- `tool_spec.json` - Gateway tool specification
- `README.md` - This file

---

## Implementation Notes

**Week 1 Priority:**
- Start with email monitoring only
- Basic qualification logic
- Email responses via SES

**Week 2 Enhancement:**
- Add SMS monitoring
- Add web form monitoring
- Improve qualification with AI

**Integrations:**
- Gmail API (OAuth2)
- Twilio API (webhooks)
- AWS SES (email sending)
- DynamoDB (lead storage)
