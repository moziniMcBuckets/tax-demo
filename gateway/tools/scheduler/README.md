# Scheduler Tool

**Agent:** Appointment Scheduler Agent  
**Purpose:** Check availability, book appointments, send confirmations  
**Pattern:** AgentCore Gateway tool

---

## Tools in This Package

### 1. check_availability
- **Purpose:** Check technician calendar availability
- **Inputs:** Date range, service type, location
- **Outputs:** Available time slots with technician details

### 2. get_technician_skills
- **Purpose:** Find technicians with required skills
- **Inputs:** Service type (HVAC, plumbing, electrical)
- **Outputs:** List of qualified technicians

### 3. book_appointment
- **Purpose:** Create appointment in calendar and database
- **Inputs:** Lead details, time slot, technician_id
- **Outputs:** appointment_id, confirmation details

### 4. send_confirmation
- **Purpose:** Send appointment confirmation via email and SMS
- **Inputs:** Appointment details, customer contact
- **Outputs:** Sent status

### 5. schedule_reminders
- **Purpose:** Schedule reminder emails/SMS
- **Inputs:** appointment_id, scheduled_time
- **Outputs:** Reminder schedule created

### 6. handle_reschedule
- **Purpose:** Handle rescheduling or cancellation requests
- **Inputs:** appointment_id, new_time or cancel
- **Outputs:** Updated appointment details

---

## Files to Create

- `scheduler_lambda.py` - Main Lambda handler
- `requirements.txt` - Python dependencies
- `tool_spec.json` - Gateway tool specification
- `README.md` - This file

---

## Implementation Notes

**Week 2 Priority:**
- Availability checking (Google Calendar API)
- Basic booking logic
- Email confirmations

**Week 3 Enhancement:**
- SMS confirmations
- Reminder scheduling (EventBridge)
- Reschedule handling

**Integrations:**
- Google Calendar API (OAuth2)
- Outlook Calendar API (alternative)
- AWS SES (email confirmations)
- Twilio (SMS confirmations)
- EventBridge (reminder scheduling)
- DynamoDB (appointment storage)
