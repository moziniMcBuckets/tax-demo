# Week 3 Action Plan: Build Invoice Agent & Complete Squad

**Company:** Vela (vela.ai)  
**Goal:** Complete Invoice Agent, integrate all 3 agents, close first customers  
**Week:** February 16-20, 2026

---

## 🎯 Week 3 Goals

**By Friday:**
- ✅ Invoice Agent 100% complete
- ✅ All 3 agents working together (Operations Squad complete!)
- ✅ End-to-end flow tested (Lead → Schedule → Invoice)
- ✅ First 2 paying customers signed up
- ✅ 100+ total outreach emails sent

---

## Monday (Day 11)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Set up DynamoDB invoices table (via CDK)
- [ ] Deploy table to AWS
- [ ] Build invoice generator tool (Lambda)
  - Generate invoice PDF
  - Calculate totals (subtotal, tax, total)
  - Upload PDF to S3
- [ ] Test invoice generation with sample data

**Afternoon (4 hours):**
- [ ] Build payment link creator tool (Lambda)
  - Integrate with Stripe API
  - Create payment links
  - Handle test mode vs production
- [ ] Test payment links work
- [ ] Verify Stripe webhooks configured

**Deliverable:** Invoices table created, invoice generation working

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Conduct demo call #4
- [ ] Push for close: "Want to be a beta customer?"
- [ ] Offer: 50% off first month for early adopters
- [ ] Follow up with previous demo attendees

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails (80 total)
- [ ] Call 5 warm prospects
- [ ] Post success story in 2 Facebook groups
- [ ] Engage with community

**Deliverable:** 1 demo completed, pushing for first customer

---

## Tuesday (Day 12)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Build invoice sender tool (Lambda)
  - Send invoice email with PDF attachment
  - Include payment link
  - Set due date (Net 30)
- [ ] Build payment tracker tool (Lambda)
  - Check payment status (Stripe API)
  - Handle payment webhooks
  - Update invoice status

**Afternoon (4 hours):**
- [ ] Build payment reminder tool (Lambda)
  - Send reminder emails
  - Different templates based on days overdue
  - Schedule reminders (EventBridge)
- [ ] Test all invoice tools
- [ ] Verify end-to-end invoice flow

**Deliverable:** All invoice tools working

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Conduct demo call #5
- [ ] Close first customer (goal!)
- [ ] If yes: Schedule onboarding call
- [ ] If no: Understand objections, refine pitch

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails (90 total)
- [ ] Follow up with hot prospects
- [ ] Create FAQ document based on demo questions
- [ ] Update pitch deck with FAQ

**Deliverable:** First customer signed (hopefully!), 90 emails sent

---

## Wednesday (Day 13)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Create Invoice Agent (Strands)
  - Write system prompt
  - Configure model (Haiku, temp=0.0)
  - Add all tools (generate, send, track, remind)
  - Test Invoice Agent individually

**Afternoon (4 hours):**
- [ ] Connect all 3 agents with Swarm
  - Initialize Swarm with Lead, Scheduler, Invoice
  - Configure shared memory (4-layer system)
  - Test handoffs: Lead → Scheduler → Invoice
  - Verify context preserved across handoffs

**Deliverable:** Operations Squad complete! All 3 agents working together

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Onboard first customer (if signed)
  - Collect business info
  - Connect Gmail account
  - Connect Google Calendar
  - Connect Stripe account
  - Configure settings
- [ ] OR: Conduct demo call #6

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails (100 total!)
- [ ] Celebrate 100 emails milestone
- [ ] Post in LinkedIn about progress
- [ ] Book 3 more demos for next week

**Deliverable:** First customer onboarded OR 6 demos completed

---

## Thursday (Day 14)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] End-to-end testing
  - Test: Lead email → Response → Booking → Invoice
  - Test: SMS lead → Response → Booking → Invoice
  - Test: Web form → Response → Booking → Invoice
  - Test: Error scenarios (API down, invalid data)

**Afternoon (4 hours):**
- [ ] Fix bugs found in testing
- [ ] Optimize response times
- [ ] Add error handling
- [ ] Improve logging and monitoring

**Deliverable:** Operations Squad tested and polished

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Monitor first customer's usage (if onboarded)
- [ ] Check: Leads coming in? Agent responding?
- [ ] Fix any issues immediately
- [ ] Collect feedback

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails
- [ ] Call 5 prospects who showed interest
- [ ] Push for second customer signup
- [ ] Offer: Early adopter discount (50% off first month)

**Deliverable:** First customer monitored, second customer in pipeline

---

## Friday (Day 15)

### You (Technical) - 6 hours

**Morning (3 hours):**
- [ ] Record final demo video (all 3 agents)
  - Show: Lead → Response → Booking → Invoice
  - Show: Dashboard with metrics
  - Show: Customer experience
- [ ] Update landing page with new video
- [ ] Add testimonial (if have one)

**Afternoon (3 hours):**
- [ ] Review Week 3 progress
- [ ] Document Operations Squad (README)
- [ ] Plan Week 4 (polish and launch)
- [ ] Celebrate Week 3! 🎉

**Deliverable:** Operations Squad complete and documented

---

### Partner (Sales) - 6 hours

**Morning (3 hours):**
- [ ] Review week's metrics
  - Total emails: 110
  - Demos: 6
  - Customers: 1-2 (goal)
  - Response rate: ?%
  - Demo-to-customer: ?%

**Afternoon (3 hours):**
- [ ] Analyze what's working
  - Which emails get responses?
  - Which pitch points resonate?
  - What objections come up?
- [ ] Refine approach for Week 4
- [ ] Plan launch strategy
- [ ] Celebrate Week 3! 🎉

**Deliverable:** Week 3 metrics analyzed, launch plan ready

---

## Week 3 Success Metrics

**Technical:**
- ✅ Operations Squad 100% complete
- ✅ All 3 agents working together
- ✅ End-to-end flow tested
- ✅ Demo video updated
- ✅ Ready for beta customers

**Sales:**
- ✅ 110 total outreach emails
- ✅ 6 demos completed
- ✅ 1-2 customers signed
- ✅ 5-10 hot prospects in pipeline

**Team:**
- ✅ Product-market fit signals
- ✅ Pitch refined
- ✅ Ready to scale

---

## Week 4 Preview

**You:**
- Polish Operations Squad
- Add monitoring and alerts
- Prepare for scale (10 customers)
- Build customer dashboard

**Partner:**
- Close 3-5 more customers
- Send 50 more emails
- Launch referral program
- Get first testimonials

**Goal:** 5-10 paying customers by end of Week 4

---

## Objection Handling (Based on Demos)

**"How do I know it will work?"**
- Response: "Let me set you up for free trial right now. You'll see results in 24 hours."

**"What if I don't like it?"**
- Response: "Cancel anytime. No questions asked. But our beta customers are closing 3x more leads."

**"Is it secure?"**
- Response: "Bank-level encryption. SOC 2 certified. Your data is isolated."

**"How long does setup take?"**
- Response: "10 minutes. I'll do it with you on this call."

---

## Customer Onboarding Checklist

**When customer says yes:**

**Step 1: Collect Info (5 minutes)**
- [ ] Business name
- [ ] Services offered
- [ ] Pricing (hourly rates)
- [ ] Service area
- [ ] Technician names and skills

**Step 2: Connect Accounts (5 minutes)**
- [ ] Gmail account (OAuth)
- [ ] Google Calendar (OAuth)
- [ ] Stripe account (OAuth)
- [ ] Phone number (Twilio)

**Step 3: Configure (5 minutes)**
- [ ] Business hours
- [ ] Booking buffer (30 min default)
- [ ] Reminder timing (24hr + 1hr default)
- [ ] Email templates (customize)

**Step 4: Test (5 minutes)**
- [ ] Send test lead
- [ ] Verify agent responds
- [ ] Book test appointment
- [ ] Verify everything works

**Step 5: Go Live (Immediate)**
- [ ] Turn on email monitoring
- [ ] Agents start working
- [ ] Give customer dashboard access
- [ ] Monitor for first 24 hours

**Total: 20 minutes to onboard**

---

## Notes & Learnings

**Demo insights:**
- [What questions do they ask?]
- [What objections come up?]
- [What makes them say yes?]

**Technical insights:**
- [What bugs did you find?]
- [What's harder than expected?]
- [What's easier than expected?]

**Next week focus:**
- [What to prioritize?]
- [What to improve?]

---

**Operations Squad is almost done! Week 4 is polish and launch! 🚀**
