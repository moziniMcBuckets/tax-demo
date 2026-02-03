# Week 2 Action Plan: Build Scheduler Agent

**Company:** Vela (vela.ai)  
**Goal:** Complete Scheduler Agent, test handoffs, book first demos  
**Week:** February 9-13, 2026

---

## 🎯 Week 2 Goals

**By Friday:**
- ✅ Scheduler Agent 100% complete
- ✅ Lead → Scheduler handoff working
- ✅ 3 demo calls completed
- ✅ First customer signed up (stretch goal)
- ✅ 50 total outreach emails sent

---

## Monday (Day 6)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Review Week 1 progress (Lead Response Agent status)
- [ ] Fix any bugs from Week 1
- [ ] Set up DynamoDB appointments table (via CDK)
- [ ] Set up DynamoDB technicians table (via CDK)
- [ ] Deploy tables to AWS

**Afternoon (4 hours):**
- [ ] Build availability checker tool (Lambda)
  - Query Google Calendar API
  - Check technician skills
  - Find available time slots
- [ ] Test availability checker with sample data
- [ ] Document tool behavior

**Deliverable:** Appointments tables created, availability checker working

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Conduct first demo call (if booked from Week 1)
- [ ] Take detailed notes on questions/objections
- [ ] Follow up with demo attendees
- [ ] Send thank you email + next steps

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails (new prospects)
- [ ] Follow up with 10 people who opened but didn't respond
- [ ] Post in 2 Facebook groups (different angle)
- [ ] Engage with comments and DMs

**Deliverable:** 1 demo completed, 20 more outreach touches

---

## Tuesday (Day 7)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Build appointment booking tool (Lambda)
  - Create calendar event (Google Calendar API)
  - Store in DynamoDB appointments table
  - Handle conflicts and errors
- [ ] Test booking with sample appointments
- [ ] Verify calendar events created correctly

**Afternoon (4 hours):**
- [ ] Build confirmation sender tool (Lambda)
  - Send email confirmation (SES)
  - Send SMS confirmation (Twilio)
  - Include appointment details
- [ ] Test confirmations sent correctly
- [ ] Verify email and SMS delivery

**Deliverable:** Booking and confirmation tools working

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Conduct demo call #2
- [ ] Refine pitch based on feedback from call #1
- [ ] Update pitch deck with learnings
- [ ] Practice objection handling

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails
- [ ] Connect with 20 prospects on LinkedIn
- [ ] Share demo video in 1 Facebook group
- [ ] Book 2 more demos for later this week

**Deliverable:** 2 demos completed, 30 more outreach touches

---

## Wednesday (Day 8)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Build reminder scheduler tool (Lambda)
  - Create EventBridge rules
  - Schedule 24hr and 1hr reminders
  - Handle reminder sending
- [ ] Test reminder scheduling
- [ ] Verify reminders trigger correctly

**Afternoon (4 hours):**
- [ ] Create Scheduler Agent (Strands)
  - Write system prompt
  - Configure model (Haiku, temp=0.0)
  - Add all tools (availability, booking, confirmation, reminders)
  - Add handoff_to_agent tool
- [ ] Test Scheduler Agent individually

**Deliverable:** Scheduler Agent complete and tested

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Conduct demo call #3
- [ ] Ask for referrals from previous demo attendees
- [ ] Send case study draft to beta testers (if any)
- [ ] Collect testimonials

**Afternoon (4 hours):**
- [ ] Send 10 more outreach emails
- [ ] Follow up with all demo attendees
- [ ] Post success story in Facebook group (if any)
- [ ] Update CRM with all interactions

**Deliverable:** 3 demos completed, pipeline building

---

## Thursday (Day 9)

### You (Technical) - 8 hours

**Morning (4 hours):**
- [ ] Connect Lead Response Agent to Scheduler Agent
  - Configure Swarm with both agents
  - Test handoff from Lead to Scheduler
  - Verify context passed correctly
  - Test shared memory working

**Afternoon (4 hours):**
- [ ] Test complete flow: Lead → Schedule
  - Send test email
  - Verify Lead Response qualifies
  - Verify handoff to Scheduler
  - Verify appointment booked
  - Verify confirmation sent
- [ ] Fix any handoff issues
- [ ] Optimize response times

**Deliverable:** Lead → Scheduler flow working end-to-end

---

### Partner (Sales) - 8 hours

**Morning (4 hours):**
- [ ] Send 10 more outreach emails
- [ ] Call 5 prospects who showed interest
- [ ] Book 2 more demos for next week
- [ ] Update target list with notes

**Afternoon (4 hours):**
- [ ] Create simple case study (even if just beta)
  - Problem: Missed leads
  - Solution: Vela Operations Squad
  - Result: Responds in 60 seconds
- [ ] Share case study with prospects
- [ ] Post in LinkedIn

**Deliverable:** 60 total outreach emails sent, case study created

---

## Friday (Day 10)

### You (Technical) - 6 hours

**Morning (3 hours):**
- [ ] Add seed data for testing
  - 3 sample technicians
  - Sample availability
  - Sample pricing
- [ ] Test with realistic scenarios
- [ ] Record updated demo video (Lead + Scheduler)

**Afternoon (3 hours):**
- [ ] Review Week 2 progress
- [ ] Document what you've built
- [ ] Plan Week 3 (Invoice Agent)
- [ ] Celebrate Week 2! 🎉

**Deliverable:** Week 2 complete, 2 agents working

---

### Partner (Sales) - 6 hours

**Morning (3 hours):**
- [ ] Review week's metrics
  - Emails sent: 60
  - Responses: ?
  - Demos: 3
  - Customers: ?
- [ ] Analyze what's working
- [ ] Refine approach for Week 3

**Afternoon (3 hours):**
- [ ] Send 10 more outreach emails (70 total)
- [ ] Follow up with hot prospects
- [ ] Plan Week 3 outreach strategy
- [ ] Celebrate Week 2! 🎉

**Deliverable:** Week 2 metrics documented, strategy refined

---

## Week 2 Success Metrics

**Technical:**
- ✅ Scheduler Agent complete
- ✅ 2 agents working together (Lead + Scheduler)
- ✅ Handoffs successful
- ✅ Demo video updated

**Sales:**
- ✅ 70 total outreach emails sent
- ✅ 3 demos completed
- ✅ 5-10 responses received
- ✅ 2-3 hot prospects identified

**Team:**
- ✅ Momentum maintained
- ✅ Learning from demos
- ✅ Refining pitch

---

## Week 3 Preview

**You:**
- Build Invoice Agent
- Connect all 3 agents
- Test complete Operations Squad

**Partner:**
- Conduct 5 more demos
- Close first 2 customers
- Send 50 more emails
- Build referral pipeline

---

## Notes & Learnings

**What worked this week:**
- [Document here]

**What didn't work:**
- [Document here]

**Changes for next week:**
- [Document here]

**Customer feedback:**
- [Document here]

---

**Keep building! Week 3 is when it all comes together! 💪**
