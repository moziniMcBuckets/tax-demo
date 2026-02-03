# How Operations Squad Works & Demo Strategy

**For:** Vela Operations Squad  
**Audience:** You (to understand) + Customers (to demo)

---

## How It Works: End-to-End Flow

### **Scenario: New Lead Inquiry**

**Step 1: Lead Comes In**
- Customer sends email to: service@acmeplumbing.com
- Subject: "Need emergency plumbing repair"
- Body: "Hi, I have a burst pipe in my basement. Need help ASAP. My name is John Smith, 555-1234"

**Step 2: Lead Response Agent Activates (60 seconds)**
- Gmail API detects new email
- Triggers Lead Response Agent
- Agent reads email content
- Agent extracts: Name (John Smith), Phone (555-1234), Service (plumbing), Urgency (emergency)

**Step 3: Agent Qualifies Lead**
- Calls qualify_lead tool
- Checks: Has contact info? Yes. Has service need? Yes. In service area? Yes.
- Score: 9/10 (emergency, has contact, clear need)
- Status: QUALIFIED

**Step 4: Agent Responds**
- Calls send_response tool
- Sends email reply:

```
Hi John,

Thanks for reaching out! I see you have an emergency plumbing situation.

We can help! I'm checking our technician availability now and will 
have someone there as soon as possible.

What's your address?

- Vela AI Assistant for Acme Plumbing
```

**Step 5: Customer Replies**
- "123 Main St, Anytown, USA 12345"

**Step 6: Agent Hands Off to Scheduler**
- Calls handoff_to_scheduler tool
- Passes context: John Smith, 555-1234, emergency plumbing, 123 Main St

**Step 7: Scheduler Agent Takes Over**
- Receives full context from shared memory
- Calls check_availability tool
- Finds: Technician Mike available in 2 hours
- Calls book_appointment tool
- Creates calendar event for Mike at 2pm today

**Step 8: Scheduler Sends Confirmation**
- Calls send_confirmation tool
- Sends email + SMS to John:

```
Appointment Confirmed! ✓

Technician: Mike Johnson
Time: Today at 2:00 PM
Service: Emergency plumbing repair
Address: 123 Main St

Mike will call 15 minutes before arrival.

Need to reschedule? Reply to this message.

- Acme Plumbing
```

**Step 9: Scheduler Schedules Reminders**
- Calls schedule_reminders tool
- Sets EventBridge rules:
  - 1 hour before: "Mike will arrive in 1 hour"
  - 15 minutes before: "Mike is on his way"

**Step 10: Scheduler Hands Off to Invoice Agent**
- Calls handoff_to_invoice tool
- Passes context: Appointment details, customer info
- Invoice Agent creates draft invoice (status: draft)

**Step 11: Appointment Happens**
- Mike arrives, fixes pipe
- Mike marks appointment "completed" in system (via mobile app or manual update)

**Step 12: Invoice Agent Activates**
- Detects appointment status changed to "completed"
- Calls generate_invoice tool
- Creates invoice:
  - Labor: 2 hours × $150/hr = $300
  - Materials: $75
  - Subtotal: $375
  - Tax (8%): $30
  - Total: $405

**Step 13: Invoice Agent Sends Invoice**
- Calls create_payment_link tool (Stripe)
- Calls send_invoice tool
- Sends email to John:

```
Invoice #1234 - Acme Plumbing

Service: Emergency plumbing repair
Date: February 2, 2026
Technician: Mike Johnson

Labor (2 hours @ $150/hr): $300.00
Materials: $75.00
Subtotal: $375.00
Tax (8%): $30.00
Total: $405.00

Pay online: [Stripe payment link]
Due: March 4, 2026 (Net 30)

Thank you for your business!
```

**Step 14: Invoice Agent Schedules Reminders**
- Calls schedule_payment_reminders tool
- Sets EventBridge rules:
  - 3 days before due: "Payment due soon"
  - On due date: "Payment due today"
  - 3 days after: "Payment overdue"
  - 7, 14, 30 days after: Escalating reminders

**Step 15: Customer Pays**
- John clicks Stripe link
- Pays $405
- Stripe webhook triggers payment_status_handler
- Invoice status updated to "paid"
- Reminders cancelled

**Step 16: Invoice Agent Syncs to Accounting**
- Calls sync_to_accounting tool
- Updates QuickBooks with invoice and payment
- Job complete! ✓

---

## How to Demo This

### **Demo Strategy: Live Simulation**

**Setup (Before Demo):**
1. Have test environment ready
2. Use your own email as "customer"
3. Have dashboard open showing empty state
4. Have phone ready to show SMS

**Demo Flow (15 minutes):**

**Part 1: The Problem (2 minutes)**
- "Let me show you what happens now when a lead comes in..."
- "You're on a job site. Phone rings. You miss it."
- "By the time you call back, they've hired someone else."
- "This happens 62% of the time. That's $10K+/month in lost revenue."

**Part 2: The Solution (8 minutes)**

**Live Demo:**

"Watch what happens with Vela..."

**Action 1: Send test email**
- Open Gmail on your phone
- Send email to: demo@vela.ai (your test account)
- Subject: "Need HVAC repair urgently"
- Body: "Hi, my AC stopped working. Need help today. John Smith, 555-1234"

**Action 2: Show agent response (60 seconds)**
- Switch to dashboard
- Show: Lead appears in real-time
- Show: Agent is typing...
- Show: Agent response sent

**Read the response:**
```
Hi John,

Thanks for reaching out! I see you need urgent HVAC repair.

We can help! I'm checking our technician availability now.

What's your address?

- Vela AI Assistant
```

**Action 3: Reply as customer**
- Reply: "123 Main St, Anytown 12345"

**Action 4: Show scheduling (2 minutes)**
- Show: Scheduler Agent takes over
- Show: Checks calendar
- Show: Books appointment
- Show: Sends confirmation

**Read confirmation:**
```
Appointment Confirmed! ✓

Technician: Mike Johnson
Time: Today at 4:00 PM
Service: HVAC repair
Address: 123 Main St

Mike will call 15 minutes before arrival.
```

**Action 5: Show SMS (if time)**
- Show: SMS confirmation on phone
- Show: Reminder scheduled

**Action 6: Show invoice (mock)**
- "After Mike completes the job..."
- Show: Invoice generated automatically
- Show: Payment link sent
- Show: Payment reminders scheduled

**Part 3: The ROI (3 minutes)**

"Here's the math:
- You currently miss 62% of leads
- That's 6 out of 10 lost
- Average job value: $2,000
- Lost revenue: $12,000/month

With Vela:
- We respond in 60 seconds (vs hours)
- We book appointments automatically
- We send invoices and track payments

If we help you close just ONE extra job per month:
- Revenue: $2,000
- Vela cost: $499
- ROI: 4x

But our customers close 3x more leads, so the real ROI is much higher."

**Part 4: The Close (2 minutes)**

"Want to try it? 14-day free trial. I can have you set up in 10 minutes."

[If yes: Book onboarding call]
[If no: "What questions do you have?"]

---

## Demo Variations

### **Option 1: Pre-Recorded Video (Safer)**

**Pros:**
- No technical issues
- Perfect every time
- Can edit and polish
- Reusable

**Cons:**
- Less impressive
- Can't customize
- Feels less real

**When to use:** Early demos, cold outreach, website

---

### **Option 2: Live Demo (More Impressive)**

**Pros:**
- More impressive
- Shows it's real
- Can customize
- Interactive

**Cons:**
- Technical issues possible
- Requires working system
- More stressful

**When to use:** Qualified prospects, later-stage demos

---

### **Option 3: Hybrid (Best)**

**Use pre-recorded video for:**
- Initial explanation
- Complex flows
- Perfect execution

**Use live demo for:**
- Simple interactions
- Q&A
- Customization

**Flow:**
1. Show pre-recorded video (3 min)
2. Do live demo of one interaction (2 min)
3. Answer questions (5 min)
4. Close (2 min)

---

## Demo Environment Setup

### **What You Need:**

**Test Account:**
- Email: demo@vela.ai
- Phone: Twilio test number
- Calendar: Google Calendar (test account)
- Stripe: Test mode

**Test Data:**
- 2-3 test technicians
- Sample availability
- Sample pricing

**Dashboard:**
- Show leads in real-time
- Show appointments booked
- Show invoices sent
- Show metrics (response time, conversion rate)

### **Demo Script Variations**

**For Plumbers:**
- Service: "Burst pipe emergency"
- Urgency: "Need help ASAP"
- Show: Fast response, emergency scheduling

**For HVAC:**
- Service: "AC stopped working"
- Urgency: "It's 95 degrees"
- Show: Same-day appointment

**For Electricians:**
- Service: "Outlet not working"
- Urgency: "This week"
- Show: Flexible scheduling

---

## Objection Handling

**"How do I know it will work for my business?"**
- "Great question. Let me show you with YOUR business info..."
- Customize demo with their company name
- Use their service types
- Show their branding (if time)

**"What if the AI makes a mistake?"**
- "The AI qualifies leads, but YOU control the calendar"
- "You can override any booking"
- "You get notified of every interaction"
- "Think of it as a really good assistant, not a replacement"

**"Is it secure?"**
- "Yes. Bank-level encryption. SOC 2 certified."
- "Your data is isolated from other customers"
- "We never share or sell your data"

**"What if I don't like it?"**
- "14-day free trial. Cancel anytime. No questions asked."
- "Most customers see ROI in the first week"

**"How long does setup take?"**
- "10 minutes. I'll do it with you on this call if you want."
- "Connect your email, calendar, and payment processor"
- "That's it. Agents go live immediately"

**"What if a lead needs something complex?"**
- "Agent escalates to you automatically"
- "You get notified: 'This lead needs human attention'"
- "You take over and handle it"
- "Agent learns from how you handle it"

---

## Customer Onboarding Flow

**After they say yes:**

**Step 1: Onboarding Call (30 minutes)**
- Collect: Business info, services offered, pricing
- Connect: Gmail account (OAuth)
- Connect: Google Calendar (OAuth)
- Connect: Stripe account (OAuth)
- Configure: Business hours, service area, technicians

**Step 2: Test Together (10 minutes)**
- Send test lead
- Watch agent respond
- Book test appointment
- Verify everything works

**Step 3: Go Live (Immediate)**
- Turn on email monitoring
- Agents start working
- Customer gets dashboard access
- You monitor for first 24 hours

**Step 4: Check-in (24 hours later)**
- Email: "How's it going? Any questions?"
- Review: First interactions
- Optimize: Based on feedback

---

## Dashboard for Customers

**What they see:**

**Overview Tab:**
- Leads today: 5 (3 qualified, 2 not qualified)
- Appointments booked: 3
- Invoices sent: 2
- Response time: 45 seconds average

**Leads Tab:**
- List of all leads
- Status: New, Qualified, Scheduled, Converted, Lost
- Click to see conversation

**Appointments Tab:**
- Calendar view
- List view
- Filter by technician, status
- Click to see details

**Invoices Tab:**
- List of all invoices
- Status: Sent, Paid, Overdue
- Click to see invoice PDF
- Payment status

**Settings Tab:**
- Business info
- Technicians
- Pricing
- Integrations
- Notifications

---

## Demo Tips

**Do:**
- ✅ Show real-time (even if pre-recorded)
- ✅ Use their business name in demo
- ✅ Focus on ROI (money saved/made)
- ✅ Keep it simple (don't overwhelm)
- ✅ Ask for the sale

**Don't:**
- ❌ Get too technical
- ❌ Show bugs or errors
- ❌ Talk about features they don't need
- ❌ Forget to close
- ❌ Undersell the value

**Remember:**
- They don't care HOW it works
- They care WHAT it does for them
- Focus on: More leads, more appointments, more revenue
- Keep it under 15 minutes
- Always be closing

---

## Quick Demo (5 Minutes)

**For busy prospects:**

"Let me show you in 5 minutes..."

**Minute 1: Problem**
- "You miss 62% of leads. That's $10K+/month lost."

**Minute 2-3: Solution**
- [Show 2-minute video]
- "Our AI responds in 60 seconds, books appointments, sends invoices"

**Minute 4: ROI**
- "Close 1 extra $2,000 job = 4x ROI"
- "Our customers close 3x more leads"

**Minute 5: Close**
- "$499/month. 14-day free trial. Want to try it?"

---

## Demo Video Script (3 Minutes)

**Scene 1: The Problem (30 seconds)**
- Show: Phone ringing, going to voicemail
- Text overlay: "62% of calls go unanswered"
- Show: Customer calling competitor
- Text overlay: "85% won't call back"
- Text overlay: "$10,000+ lost per month"

**Scene 2: The Solution (90 seconds)**
- Show: Email coming in
- Show: Vela dashboard lighting up
- Show: Agent typing response
- Show: Response sent (60 seconds elapsed)
- Show: Customer replies
- Show: Scheduler Agent booking appointment
- Show: Confirmation sent
- Show: Calendar updated

**Scene 3: The Result (60 seconds)**
- Show: Dashboard with metrics
  - 10 leads today
  - 8 qualified (80%)
  - 6 appointments booked (75%)
  - Average response time: 45 seconds
- Show: Invoice sent after job
- Show: Payment received
- Text overlay: "3x more leads closed"
- Text overlay: "15+ hours saved per week"
- Text overlay: "$499/month"

**End screen:**
- "Try Vela free for 14 days"
- "vela.ai"

---

## Testing Strategy (Before Demos)

### **Week 1-2: Internal Testing**

**Test 1: Email Response**
- Send test email
- Verify: Agent responds in <60 seconds
- Verify: Response is appropriate
- Verify: Lead stored in database

**Test 2: Lead Qualification**
- Send 10 different test leads
- Verify: Qualified correctly (8/10 accuracy minimum)
- Verify: Appropriate responses
- Verify: Handoffs work

**Test 3: Appointment Booking**
- Qualify test lead
- Verify: Scheduler takes over
- Verify: Checks availability correctly
- Verify: Books appointment
- Verify: Sends confirmation

**Test 4: End-to-End**
- Lead → Qualify → Schedule → Invoice
- Verify: All handoffs work
- Verify: Context preserved
- Verify: No errors

### **Week 3-4: Beta Testing**

**Recruit 3 beta customers:**
- Offer: Free for 30 days
- Ask: Detailed feedback
- Monitor: Every interaction
- Fix: Issues immediately

**Beta customer criteria:**
- Friendly and patient
- Tech-savvy enough to help troubleshoot
- Willing to give feedback
- Ideally: Someone you know

---

## Demo Environments

### **Environment 1: Development**
- Your local machine
- Test data only
- For building and testing

### **Environment 2: Staging**
- AWS staging account
- Test data + beta customers
- For demos and beta testing

### **Environment 3: Production**
- AWS production account
- Real customers only
- For paying customers

**Demo from Staging environment** (not production)

---

## Common Demo Scenarios

### **Scenario 1: Emergency Service**
- Lead: "Burst pipe, need help NOW"
- Show: Immediate response, same-day booking
- Emphasize: Speed and urgency handling

### **Scenario 2: Routine Service**
- Lead: "Need AC tune-up before summer"
- Show: Flexible scheduling, multiple options
- Emphasize: Convenience and professionalism

### **Scenario 3: Price Shopping**
- Lead: "How much for water heater installation?"
- Show: Agent asks qualifying questions
- Show: Agent provides range, books estimate
- Emphasize: Lead capture and conversion

### **Scenario 4: After Hours**
- Lead: Comes in at 11pm
- Show: Agent still responds immediately
- Show: Books appointment for next day
- Emphasize: 24/7 availability

---

## Dashboard Demo

**Show them their future dashboard:**

**Metrics Card:**
```
Today's Performance
- Leads: 12 (↑ 3 from yesterday)
- Qualified: 9 (75%)
- Booked: 7 (78% conversion)
- Response time: 52 seconds avg
```

**Recent Activity:**
```
2:34 PM - New lead: John Smith (HVAC repair)
2:35 PM - Qualified (Score: 9/10)
2:36 PM - Appointment booked (Tomorrow 2pm)
2:37 PM - Confirmation sent

1:15 PM - New lead: Jane Doe (Plumbing)
1:16 PM - Qualified (Score: 7/10)
1:17 PM - Appointment booked (Friday 10am)
```

**Upcoming Appointments:**
```
Today:
- 4:00 PM - Mike Johnson → Emergency plumbing (John Smith)

Tomorrow:
- 10:00 AM - Sarah Lee → AC repair (Bob Wilson)
- 2:00 PM - Mike Johnson → HVAC repair (John Smith)
```

---

## The "Wow" Moment

**What makes them say "I need this":**

**Moment 1: 60-Second Response**
- Show email coming in
- Show agent responding in real-time
- "This happens 24/7, even at 2am"

**Moment 2: Automatic Booking**
- Show agent checking calendar
- Show appointment booked
- "No back-and-forth, no phone tag"

**Moment 3: The Math**
- "You currently miss 62% of leads"
- "That's 6 out of 10 lost"
- "At $2,000 per job, that's $12,000/month"
- "Vela costs $499/month"
- "If we help you close just 1 extra job, you've made 4x your money back"

**This is when they buy.**

---

## Closing the Demo

**After demo:**

"So, what do you think?"

[Let them talk]

**If positive:**
"Great! Want to try it? 14-day free trial, I can set you up right now."

**If hesitant:**
"What concerns do you have?"
[Address objections]
"How about this - try it free for 14 days. If it doesn't work, cancel. No risk."

**If they say yes:**
"Perfect! Let me get you set up. This will take about 10 minutes..."
[Start onboarding call]

**If they say no:**
"No problem. Can I follow up in a week?"
[Set reminder, send case study]

---

## Success Metrics for Demos

**Good demo:**
- ✅ Prospect engaged (asking questions)
- ✅ "Wow" moment happened
- ✅ They see the ROI
- ✅ They want to try it

**Great demo:**
- ✅ They say "I need this"
- ✅ They ask about pricing
- ✅ They want to start immediately
- ✅ They refer others

**Track:**
- Demo-to-trial conversion: Target 40%+
- Trial-to-paid conversion: Target 60%+
- Overall: 24%+ (demo to paid)

---

## Bottom Line

**How it works:**
- Lead comes in → Agent responds → Schedules → Invoices → Done
- All automatic, 24/7, no human needed

**How to demo:**
- Show live (or video)
- Focus on ROI (money saved/made)
- Keep it simple (15 minutes max)
- Always close (ask for the sale)

**The key:**
- They don't care about the technology
- They care about closing more leads
- Show them the money
- Make it a no-brainer

**Now go build it and start demoing! 🚀**
