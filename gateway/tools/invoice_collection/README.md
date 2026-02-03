# Invoice Collection Tool

**Agent:** Invoice Collection Agent  
**Purpose:** Generate invoices, track payments, send reminders  
**Pattern:** AgentCore Gateway tool

---

## Tools in This Package

### 1. generate_invoice
- **Purpose:** Create invoice PDF with service details
- **Inputs:** appointment_id, line_items, amounts
- **Outputs:** invoice_id, PDF URL

### 2. calculate_total
- **Purpose:** Calculate invoice total (subtotal + tax)
- **Inputs:** Line items, tax rate
- **Outputs:** Subtotal, tax, total

### 3. create_payment_link
- **Purpose:** Generate Stripe or Square payment link
- **Inputs:** invoice_id, amount, customer_email
- **Outputs:** Payment link URL

### 4. send_invoice
- **Purpose:** Send invoice via email with PDF and payment link
- **Inputs:** invoice_id, customer_email, PDF URL, payment link
- **Outputs:** Sent status

### 5. check_payment_status
- **Purpose:** Check if invoice has been paid
- **Inputs:** invoice_id
- **Outputs:** Payment status, paid_date

### 6. send_payment_reminder
- **Purpose:** Send payment reminder email/SMS
- **Inputs:** invoice_id, days_overdue
- **Outputs:** Reminder sent status

### 7. schedule_payment_reminders
- **Purpose:** Schedule automatic payment reminders
- **Inputs:** invoice_id, due_date
- **Outputs:** Reminder schedule created

### 8. offer_payment_plan
- **Purpose:** Create payment plan if customer requests
- **Inputs:** invoice_id, plan_terms
- **Outputs:** Payment plan details

### 9. sync_to_accounting
- **Purpose:** Sync invoice to QuickBooks or Xero
- **Inputs:** invoice_id, invoice_details
- **Outputs:** Sync status

---

## Files to Create

- `invoice_collection_lambda.py` - Main Lambda handler
- `requirements.txt` - Python dependencies
- `tool_spec.json` - Gateway tool specification
- `README.md` - This file

---

## Implementation Notes

**Week 3 Priority:**
- Invoice generation (PDF)
- Payment link creation (Stripe)
- Email sending with attachment

**Week 4 Enhancement:**
- Payment tracking (webhooks)
- Reminder scheduling (EventBridge)
- Accounting sync (QuickBooks)

**Week 5 Enhancement:**
- Payment plans
- SMS reminders
- Advanced reporting

**Integrations:**
- Stripe API (payment links, webhooks)
- Square API (alternative)
- AWS SES (email with attachments)
- Twilio (SMS reminders)
- QuickBooks API (accounting sync)
- Xero API (alternative)
- S3 (PDF storage)
- DynamoDB (invoice storage)
