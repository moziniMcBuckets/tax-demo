# Sample Queries for Testing Tax Document Agent

This document provides sample queries to test all features of the tax document collection agent.

---

## Initial Setup Queries

### 1. Getting Started
```
Hello! I'm a new user. What can you help me with?
```

### 2. Identify Yourself
```
What's my accountant ID?
```
**Expected:** Agent asks for your accountant ID

```
acc_test_001
```
**Expected:** Agent confirms and shows your clients

---

## Client Overview Queries

### 3. View All Clients
```
Show me all my clients
```
**Expected:** List of all clients with their statuses

### 4. Client Count
```
How many clients do I have?
```
**Expected:** Total count and breakdown by status

### 5. Filter by Status
```
Show me only incomplete clients
```
**Expected:** List of clients with incomplete status

```
Which clients are complete?
```
**Expected:** List of clients who submitted all documents

```
Show me at-risk clients
```
**Expected:** Clients approaching deadline with missing docs

```
Which clients are escalated?
```
**Expected:** Clients marked as urgent/escalated

---

## Document Status Queries

### 6. Check Specific Client
```
What's the status of Mohamed Mohamud?
```
**Expected:** Detailed status with missing documents

```
Has John Smith uploaded his W-2?
```
**Expected:** Yes/No with document details

### 7. Missing Documents
```
What documents is Sarah Johnson missing?
```
**Expected:** List of missing documents

```
Show me all clients missing W-2 forms
```
**Expected:** List of clients without W-2

### 8. Document Requirements
```
What documents does Emily Davis need to submit?
```
**Expected:** Complete list of required documents

```
Add 1099-B to John Smith's requirements
```
**Expected:** Confirmation of added requirement

---

## Follow-up and Reminder Queries

### 9. Send Individual Reminders
```
Send a reminder to Mohamed Mohamud
```
**Expected:** Confirmation email sent with details

```
Send John Smith a reminder about his missing W-2
```
**Expected:** Personalized reminder sent

```
Remind Sarah Johnson that the deadline is approaching
```
**Expected:** Urgent reminder sent

### 10. Bulk Reminders
```
Send reminders to all incomplete clients
```
**Expected:** Batch email confirmation

```
Send reminders to everyone who hasn't responded in 7 days
```
**Expected:** Filtered batch reminders

### 11. Custom Messages
```
Send Mohamed a reminder and tell him I need the documents by Friday
```
**Expected:** Reminder with custom message

---

## Escalation Queries

### 12. Check Escalations
```
Which clients need escalation?
```
**Expected:** List of clients with 3+ reminders

```
Show me urgent cases
```
**Expected:** Escalated clients

### 13. Escalate Clients
```
Escalate John Smith
```
**Expected:** Escalation confirmation + notification

```
Mark Sarah Johnson as urgent
```
**Expected:** Status updated to escalated

---

## Timeline and History Queries

### 14. Follow-up History
```
Show me the follow-up history for Mohamed Mohamud
```
**Expected:** List of all reminders sent with dates

```
When was the last time I contacted John Smith?
```
**Expected:** Date of last follow-up

```
How many reminders has Sarah Johnson received?
```
**Expected:** Count and dates

### 15. Response Tracking
```
Which clients have responded to reminders?
```
**Expected:** List of responsive clients

```
Who hasn't responded to any reminders?
```
**Expected:** List of unresponsive clients

---

## Analytics and Reporting Queries

### 16. Progress Reports
```
Give me a summary of this week's progress
```
**Expected:** Overview of uploads, reminders, completions

```
How many documents were uploaded this week?
```
**Expected:** Count with breakdown

### 17. Deadline Tracking
```
Which clients are at risk of missing the deadline?
```
**Expected:** List with days remaining

```
Show me clients with deadlines in the next 7 days
```
**Expected:** Filtered list by deadline

### 18. Completion Rates
```
What's my completion rate?
```
**Expected:** Percentage of complete clients

```
How many clients have submitted all documents?
```
**Expected:** Count and percentage

---

## Proactive Agent Queries

### 19. Recommendations
```
What should I focus on today?
```
**Expected:** Prioritized action items

```
What needs my attention?
```
**Expected:** Urgent cases and recommendations

```
Who should I follow up with next?
```
**Expected:** Prioritized client list

### 20. Risk Assessment
```
Which clients are most at risk?
```
**Expected:** Risk-scored client list

```
Analyze my client portfolio
```
**Expected:** Comprehensive analysis

---

## Specific Document Queries

### 21. Document Types
```
Which clients are missing 1099 forms?
```
**Expected:** Filtered list

```
Show me all clients who submitted W-2s
```
**Expected:** List with submission dates

```
Who needs prior year tax returns?
```
**Expected:** Clients missing that document

### 22. Upload Tracking
```
What documents did Mohamed upload?
```
**Expected:** List of uploaded documents with dates

```
When did John Smith upload his W-2?
```
**Expected:** Upload date and time

---

## Bulk Operations

### 23. Mass Actions
```
Send reminders to everyone missing W-2 forms
```
**Expected:** Batch operation confirmation

```
Escalate all clients with 3+ reminders
```
**Expected:** Bulk escalation

```
Show me the status of all clients in alphabetical order
```
**Expected:** Sorted client list

```
Send upload links to all incomplete clients
```
**Expected:** Batch upload link sending

---

## Upload Link Queries

### 24. Send Upload Links
```
Send John Smith his upload link
```
**Expected:** Upload link generated and emailed

```
Send Mohamed his upload link with a note that I need it by Friday
```
**Expected:** Upload link with custom message

```
Generate an upload link for Sarah Johnson valid for 60 days
```
**Expected:** Extended validity upload link

```
Send upload links to all new clients
```
**Expected:** Bulk upload link operation

---

## Edge Cases and Error Handling

### 25. Invalid Queries
```
Show me client XYZ123
```
**Expected:** "Client not found" message

```
Send a reminder to nonexistent@email.com
```
**Expected:** Error handling

### 25. Ambiguous Queries
```
Send a reminder
```
**Expected:** Agent asks "To which client?"

```
Check the status
```
**Expected:** Agent asks "Of which client?"

---

## Complex Multi-Step Queries

### 26. Workflow Queries
```
Check Mohamed's status, and if he's missing documents, send him a reminder
```
**Expected:** Status check + conditional reminder

```
Show me all incomplete clients, then send reminders to those who haven't been contacted in 7 days
```
**Expected:** Multi-step operation

### 27. Conditional Actions
```
If John Smith hasn't uploaded his W-2 by tomorrow, escalate him
```
**Expected:** Scheduled action or recommendation

---

## Natural Language Variations

### 28. Casual Language
```
Hey, what's up with Mohamed?
```
**Expected:** Status update

```
Did John send his stuff yet?
```
**Expected:** Document status

```
Shoot Sarah an email about her docs
```
**Expected:** Reminder sent

### 29. Formal Language
```
Please provide a comprehensive status report for client Mohamed Mohamud
```
**Expected:** Detailed formal report

```
I require a list of all outstanding document submissions
```
**Expected:** Formal list

---

## Time-Based Queries

### 30. Recent Activity
```
What happened today?
```
**Expected:** Today's uploads and activities

```
Show me this week's uploads
```
**Expected:** Weekly summary

```
What changed since yesterday?
```
**Expected:** Delta report

### 31. Historical Queries
```
How many reminders did I send last month?
```
**Expected:** Historical count

```
Show me all uploads from January
```
**Expected:** Filtered historical data

---

## Comparison Queries

### 32. Client Comparisons
```
Compare Mohamed and John's progress
```
**Expected:** Side-by-side comparison

```
Who's doing better, Sarah or Emily?
```
**Expected:** Comparative analysis

---

## Testing Specific Tools

### 33. Document Checker Tool
```
Check what documents Mohamed is missing
```
**Expected:** Uses document_checker tool

### 34. Email Sender Tool
```
Send Mohamed a reminder email
```
**Expected:** Uses send_followup_email tool

### 35. Status Tracker Tool
```
Give me an overview of all my clients
```
**Expected:** Uses status_tracker tool

### 36. Escalation Manager Tool
```
Escalate John Smith
```
**Expected:** Uses escalation_manager tool

### 37. Requirement Manager Tool
```
Add 1099-B to Sarah's requirements
```
**Expected:** Uses requirement_manager tool

### 38. Send Upload Link Tool
```
Send John Smith his upload link
```
**Expected:** Uses send_upload_link tool

```
Send upload links to all new clients
```
**Expected:** Uses send_upload_link tool multiple times

---

## Conversation Flow Testing

### 39. Multi-Turn Conversations
```
Turn 1: "Show me my clients"
Turn 2: "Send reminders to the incomplete ones"
Turn 3: "How many emails did we just send?"
```
**Expected:** Context maintained across turns

### 39. Clarification Handling
```
You: "Send a reminder"
Agent: "To which client?"
You: "Mohamed"
Agent: "Reminder sent to Mohamed Mohamud"
```
**Expected:** Proper clarification flow

---

## Memory Testing

### 40. Context Retention
```
Turn 1: "My accountant ID is acc_test_001"
Turn 2: "Show me my clients"
Turn 3: "Send reminders to incomplete ones"
```
**Expected:** Agent remembers accountant ID

### 41. Preference Learning
```
Turn 1: "I prefer to see clients sorted by deadline"
Turn 2: "Show me my clients"
```
**Expected:** Agent applies preference

---

## Error Recovery

### 42. Graceful Failures
```
Send a reminder to a client with no email address
```
**Expected:** Clear error message + suggestion

```
Check status of a deleted client
```
**Expected:** Helpful error message

---

## Performance Testing

### 43. Large Dataset Queries
```
Show me all clients (if you have 50+)
```
**Expected:** Paginated or summarized results

```
Send reminders to all incomplete clients (bulk operation)
```
**Expected:** Efficient batch processing

---

## Integration Testing

### 44. End-to-End Workflows

**Workflow 1: New Client Onboarding**
```
1. "Add client John Doe with email john@example.com"
2. "Set his requirements to W-2, 1099-INT, and prior year return"
3. "Send him his upload link"
4. "Check his status"
```

**Workflow 2: Follow-up Campaign**
```
1. "Show me all clients who haven't uploaded in 7 days"
2. "Send them all reminders"
3. "Mark the ones with 3+ reminders as escalated"
4. "Give me a summary of what we just did"
```

**Workflow 3: Deadline Management**
```
1. "Which clients have deadlines in the next 3 days?"
2. "Send urgent reminders to those missing documents"
3. "Escalate anyone who doesn't respond by tomorrow"
```

---

## Quick Test Script

### Copy-Paste Test Sequence (5 minutes)

```
1. acc_test_001
2. Show me all my clients
3. What's the status of Mohamed Mohamud?
4. Send him a reminder
5. Which clients are at risk?
6. Send reminders to all incomplete clients
7. Escalate John Smith
8. Give me a summary of today's activity
9. What should I focus on next?
10. Thank you!
```

---

## Expected Tool Usage

| Query | Expected Tool |
|-------|---------------|
| "Show me all clients" | status_tracker |
| "What's Mohamed missing?" | document_checker |
| "Send a reminder" | send_followup_email |
| "Escalate John" | escalation_manager |
| "Add 1099-B requirement" | requirement_manager |
| "Check upload status" | document_checker |

---

## Success Criteria

✅ Agent responds within 3-5 seconds  
✅ Correct tool selected for each query  
✅ Natural, conversational responses  
✅ Accurate data from DynamoDB  
✅ Emails sent successfully via SES  
✅ Context maintained across conversation  
✅ Graceful error handling  
✅ Helpful suggestions and proactive recommendations  

---

## Troubleshooting Queries

If something doesn't work:

```
"What tools do you have access to?"
"Can you check if the gateway is working?"
"Show me your capabilities"
"What's your system status?"
```

---

**Pro Tip:** Start with simple queries and gradually increase complexity to test different aspects of the system!
