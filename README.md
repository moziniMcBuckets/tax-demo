# RainCity Operations Squad

**Company:** RainCity (raincity.ai)  
**Status:** 🚀 In Development - Week 1  
**Launch Target:** 4 weeks

An intelligent AI squad built on Amazon Bedrock AgentCore that automates operations for home services businesses. Three specialized agents work together using Swarm orchestration to handle lead response, appointment scheduling, and invoice collection.

**Tagline:** "AI That Works Rain or Shine"  
**Target Market:** Home services (plumbers, HVAC, electricians, contractors, landscapers)

---

## What It Does

The Vela Operations Squad automates your operations from lead to payment:

- **Responds to leads instantly** - Email, SMS, website forms in under 60 seconds, 24/7
- **Qualifies leads automatically** - Intelligent questions, scores 1-10, routes appropriately
- **Books appointments** - Checks calendar, finds best slot, sends confirmations
- **Sends reminders** - 24hr and 1hr before appointments (reduces no-shows 60%)
- **Generates invoices** - PDF invoices with payment links after service completion
- **Tracks payments** - Monitors status, sends reminders if overdue
- **Handles collections** - Automated reminder sequence, escalates if needed

## The Three Agents

**1. Lead Response Agent**
- Monitors email, SMS, website forms
- Responds within 60 seconds
- Qualifies leads (score 1-10)
- Hands off to Scheduler if qualified

**2. Appointment Scheduler Agent**
- Checks technician availability
- Books appointments automatically
- Sends email + SMS confirmations
- Schedules reminders

**3. Invoice Collection Agent**
- Generates invoice PDFs
- Creates Stripe payment links
- Sends invoices via email
- Tracks payments, sends reminders

**They work together using Swarm pattern** - autonomous handoffs with shared context.

---

## Key Features

✅ **Multi-channel lead capture** - Email, SMS, website forms, phone (voicemail)  
✅ **Instant response** - Under 60 seconds, 24/7 availability  
✅ **Intelligent qualification** - AI-powered lead scoring  
✅ **Automatic booking** - Calendar integration (Google, Outlook)  
✅ **Smart reminders** - Reduces no-shows by 60%  
✅ **Automated invoicing** - PDF generation, payment links  
✅ **Payment tracking** - Stripe integration, reminder sequences  
✅ **Multi-tenant secure** - Data isolation per customer  
✅ **Cost-effective** - $0.52/customer/month infrastructure  
✅ **Swarm orchestration** - Agents coordinate autonomously  

---

## Quick Start

**Prerequisites:**
- AWS account with admin access
- Node.js 20+, Python 3.11+, Docker
- Gmail account (for email monitoring)
- Google Calendar (for scheduling)
- Stripe account (for payments)

**Deploy in 30 minutes:**

```bash
# 1. Install dependencies
cd infra-cdk
npm install

# 2. Configure
cp config-operations-squad.yaml config.yaml
# Edit config.yaml with your stack name and email

# 3. Deploy infrastructure
cdk bootstrap  # First time only
cdk deploy --all --require-approval never

# 4. Configure integrations
# - Verify email in SES
# - Connect Gmail (OAuth)
# - Connect Google Calendar (OAuth)
# - Connect Stripe

# 5. Test
python3 scripts/test-operations-squad.py
```

See [Week 1 Action Plan](docs/WEEK_1_ACTION_PLAN.md) for detailed steps.

---

## Architecture

```
Lead comes in (email/SMS/form)
    ↓
Lead Response Agent (60 seconds)
  - Qualifies lead
  - Responds to customer
  - Hands off to Scheduler
    ↓
Scheduler Agent (2 minutes)
  - Checks availability
  - Books appointment
  - Sends confirmation
  - Hands off to Invoice
    ↓
Invoice Agent (after service)
  - Generates invoice
  - Sends with payment link
  - Tracks payment
  - Sends reminders
```

**Technology Stack:**
- **Agents:** Strands SDK with Swarm pattern
- **Model:** Claude 3.5 Haiku (cost-optimized)
- **Memory:** AgentCore Memory (4-layer system)
- **Tools:** 21 tools across 9 Lambda functions
- **Data:** 4 DynamoDB tables (leads, appointments, technicians, invoices)
- **Integrations:** Gmail, Calendar, Stripe, Twilio, SES

---

## Documentation

### **Getting Started**
- **[START_HERE.md](docs/START_HERE.md)** - Quick overview and Week 1 tasks
- **[BUSINESS_PLAN.md](docs/BUSINESS_PLAN.md)** - Complete strategy and market validation
- **[WEEK_1_ACTION_PLAN.md](docs/WEEK_1_ACTION_PLAN.md)** - Day-by-day execution plan

### **Technical Guides**
- **[TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md)** - Architecture and implementation
- **[OPERATIONS_SQUAD_IMPLEMENTATION_GUIDE.md](docs/OPERATIONS_SQUAD_IMPLEMENTATION_GUIDE.md)** - Swarm pattern, memory, models
- **[OPERATIONS_SQUAD_BEST_PRACTICES.md](docs/OPERATIONS_SQUAD_BEST_PRACTICES.md)** - Lessons learned, AWS best practices
- **[LOCAL_TESTING_GUIDE.md](docs/LOCAL_TESTING_GUIDE.md)** - Test locally without AWS

### **Execution Plans**
- **[WEEK_2_ACTION_PLAN.md](docs/WEEK_2_ACTION_PLAN.md)** - Build Scheduler Agent
- **[WEEK_3_ACTION_PLAN.md](docs/WEEK_3_ACTION_PLAN.md)** - Build Invoice Agent
- **[WEEK_4_ACTION_PLAN.md](docs/WEEK_4_ACTION_PLAN.md)** - Polish and launch
- **[WEEK_5_ACTION_PLAN.md](docs/WEEK_5_ACTION_PLAN.md)** - Scale to 15-20 customers

### **Sales & Demo**
- **[HOW_IT_WORKS_AND_DEMO_STRATEGY.md](docs/HOW_IT_WORKS_AND_DEMO_STRATEGY.md)** - Demo playbook and sales strategy

---

## Project Structure

```
vela-operations-squad/
├── docs/                    # Documentation
│   ├── START_HERE.md       # ⭐ Start here
│   ├── BUSINESS_PLAN.md
│   ├── TECHNICAL_GUIDE.md
│   └── WEEK_*_ACTION_PLAN.md
├── patterns/
│   └── strands-multi-agent/
│       └── operations_squad.py  # 3 agents with Swarm
├── gateway/
│   ├── tools/
│   │   ├── lead_response/       # Lead Response Agent tools
│   │   ├── scheduler/           # Scheduler Agent tools
│   │   └── invoice_collection/  # Invoice Agent tools
│   └── layers/common/           # Shared utilities
├── infra-cdk/               # AWS CDK infrastructure
│   ├── lib/
│   │   ├── database-stack.ts    # DynamoDB tables
│   │   ├── backend-stack.ts     # AgentCore + Lambda
│   │   └── cognito-stack.ts     # Authentication
│   └── config-operations-squad.yaml
├── scripts/                 # Testing and deployment
│   ├── test-operations-squad.py
│   ├── test-lead-response.py
│   └── seed-test-data.py
└── README.md (this file)
```

---

## Cost Analysis

**Infrastructure cost per customer:**
- AgentCore Runtime: $0.30/month
- Lambda (9 functions): $0.06/month
- DynamoDB (4 tables): $0.04/month
- S3 (documents): $0.01/month
- External APIs: $0.11/month
- **Total: $0.52/customer/month**

**At scale:**
- 50 customers: $26/month infrastructure
- Revenue: 50 × $499 = $24,950/month
- **Gross margin: 99.9%**

---

## Why RainCity?

Like Seattle's reliable rain, RainCity AI works consistently—rain or shine, day or night. Your operations run smoothly 24/7, just like clockwork.

---

## Market Validation

**AI Agents Market:**
- 2026: $11.78B (growing 46.6% annually)
- Gartner: 40% of enterprise apps will have AI agents by end of 2026

**Home Services Pain:**
- Miss 62% of calls (industry research)
- 85% of customers won't call back
- $10K+/month lost revenue per business

**Willingness to Pay:**
- ServiceTitan: $300-500/month per user
- AI answering services: $597-2,495/month
- **Vela: $499/month total (33-84% cheaper)**

---

## Roadmap

**Week 1:** Build Lead Response Agent  
**Week 2:** Build Scheduler Agent  
**Week 3:** Build Invoice Agent  
**Week 4:** Polish and launch  
**Week 5:** Scale to 15-20 customers  
**Month 2-3:** Add Sales & Growth Squad  
**Month 4-6:** Add Professional Services Squad  

---

## Contributing

This is a commercial product. Not accepting external contributions at this time.

---

## License

Apache-2.0

---

## Contact

**Founders:** [Your Name] + [Partner Name]  
**Company:** RainCity  
**Website:** raincity.ai (launching soon)  
**Email:** founders@raincity.ai

---

**Status:** Week 1 of development. Follow along in the weekly action plans!
