# Repo Conversion Plan: Tax-Demo → Vela Operations Squad

**Goal:** Transform this repo into Vela Operations Squad  
**Approach:** Top-down (docs → config → code)  
**Timeline:** 2-3 hours  
**Status:** Planning phase - awaiting approval

---

## What We're Doing

**FROM:** Tax Document Collection Agent (single agent, single use case)  
**TO:** Vela Operations Squad (3 agents, home services operations)

---

## Conversion Steps

### **Step 1: Update Documentation (30 min)**

**Keep:**
- ✅ All new Vela docs (already created)
- ✅ ARCHITECTURE.md (update for Operations Squad)
- ✅ DEPLOYMENT.md (update for Operations Squad)
- ✅ GATEWAY.md (keep, still relevant)

**Update:**
- README.md → Vela Operations Squad
- ARCHITECTURE.md → 3 agents instead of 1
- DEPLOYMENT.md → Operations Squad deployment

**Remove:**
- Tax-specific docs (COST_ESTIMATE_10_ACCOUNTANTS.md, etc.)

---

### **Step 2: Update Configuration (15 min)**

**Update `infra-cdk/config.yaml`:**
```yaml
# FROM:
stack_name_base: tax-agent

# TO:
stack_name_base: vela-ops-squad
```

**Update agent pattern:**
```yaml
# FROM:
backend:
  pattern: strands-single-agent

# TO:
backend:
  pattern: strands-multi-agent
```

---

### **Step 3: Rename Agent Files (10 min)**

**FROM:**
```
patterns/strands-single-agent/
└── tax_document_agent.py
```

**TO:**
```
patterns/strands-multi-agent/
└── operations_squad.py
```

---

### **Step 4: Update Agent Code (1 hour)**

**Replace tax_document_agent.py with operations_squad.py:**
- 3 agents instead of 1
- Swarm orchestration
- New system prompts
- New tools (lead response, scheduler, invoice)

---

### **Step 5: Update Gateway Tools (30 min)**

**Keep structure, update tools:**

**FROM:**
```
gateway/tools/
├── document_checker/
├── email_sender/
├── status_tracker/
├── escalation_manager/
├── requirement_manager/
└── upload_manager/
```

**TO:**
```
gateway/tools/
├── lead_response/
├── scheduler/
└── invoice_collection/
```

---

### **Step 6: Update Database Schema (15 min)**

**FROM:**
- clients table
- documents table
- followups table
- settings table

**TO:**
- leads table
- appointments table
- technicians table
- invoices table
- settings table (keep)

---

### **Step 7: Update Scripts (15 min)**

**Remove:**
- seed-tax-test-data.py
- test-tax-agent.py
- test-tax-gateway.py

**Add:**
- seed-operations-test-data.py
- test-operations-squad.py
- test-lead-response.py
- test-scheduler.py
- test-invoice.py

---

### **Step 8: Update Frontend (30 min)**

**Update branding:**
- Tax Agent → Vela Operations Squad
- Accountant → Business Owner
- Client → Lead/Customer
- Documents → Leads/Appointments/Invoices

---

## Detailed File Changes

### **Files to DELETE:**
- [ ] docs/COST_ESTIMATE_10_ACCOUNTANTS.md
- [ ] docs/test1 (1).pdf
- [ ] scripts/seed-tax-test-data.py
- [ ] scripts/test-tax-agent.py
- [ ] scripts/test-tax-gateway.py
- [ ] scripts/update-client-accountant-id.py
- [ ] patterns/strands-single-agent/tax_document_agent.py

### **Files to UPDATE:**
- [ ] README.md (rebrand to Vela)
- [ ] infra-cdk/config.yaml (rename stack, update pattern)
- [ ] infra-cdk/config-tax-agent.yaml → config-operations-squad.yaml
- [ ] docs/ARCHITECTURE.md (3 agents, new flow)
- [ ] docs/DEPLOYMENT.md (Operations Squad deployment)
- [ ] docs/REPLICATION_GUIDE.md (Operations Squad replication)

### **Files to CREATE:**
- [ ] patterns/strands-multi-agent/operations_squad.py
- [ ] gateway/tools/lead_response/lead_response_lambda.py
- [ ] gateway/tools/scheduler/scheduler_lambda.py
- [ ] gateway/tools/invoice_collection/invoice_collection_lambda.py
- [ ] scripts/seed-operations-test-data.py
- [ ] scripts/test-operations-squad.py

### **Files to KEEP (No Changes):**
- [ ] gateway/layers/common/ (reuse utilities)
- [ ] docs/GATEWAY.md (still relevant)
- [ ] docs/MEMORY_INTEGRATION.md (still relevant)
- [ ] docs/STREAMING.md (still relevant)
- [ ] Makefile, pyproject.toml, ruff.toml (keep)

---

## Risk Assessment

**Low Risk:**
- Documentation updates
- Configuration changes
- New tool folders

**Medium Risk:**
- Agent code replacement
- Database schema changes
- Frontend updates

**High Risk:**
- Deleting tax-specific code (make sure you have backup!)

---

## Backup Strategy

**Before starting:**
```bash
# 1. Create backup branch
git checkout -b backup-tax-demo
git push origin backup-tax-demo

# 2. Create new branch for conversion
git checkout main
git checkout -b vela-operations-squad

# 3. Do all work in vela-operations-squad branch
# 4. Test thoroughly
# 5. Merge to main when ready
```

---

## Conversion Checklist

### **Phase 1: Documentation (Safe)**
- [ ] Update README.md
- [ ] Update ARCHITECTURE.md
- [ ] Update DEPLOYMENT.md
- [ ] Keep Vela docs (already created)
- [ ] Remove tax-specific docs

### **Phase 2: Configuration (Safe)**
- [ ] Update config.yaml
- [ ] Rename config files
- [ ] Update CDK stack names

### **Phase 3: Code Structure (Medium Risk)**
- [ ] Create new agent file (operations_squad.py)
- [ ] Create new tool folders
- [ ] Keep old code until new code works

### **Phase 4: Implementation (High Risk)**
- [ ] Implement new agents
- [ ] Implement new tools
- [ ] Test thoroughly
- [ ] Delete old code only when new code works

### **Phase 5: Testing (Critical)**
- [ ] Test locally
- [ ] Deploy to staging
- [ ] Test end-to-end
- [ ] Verify everything works

### **Phase 6: Cleanup (Final)**
- [ ] Delete old tax-specific code
- [ ] Delete old tools
- [ ] Clean up unused files
- [ ] Commit and push

---

## Estimated Time

**Total: 8-12 hours**
- Documentation: 1 hour
- Configuration: 30 min
- Code structure: 1 hour
- Implementation: 4-6 hours
- Testing: 2-3 hours
- Cleanup: 30 min

---

## Decision Point

**Option A: Convert This Repo**
- **Pros:** Keep git history, reuse infrastructure
- **Cons:** Risk breaking tax-demo, messy history
- **Time:** 8-12 hours

**Option B: Create New Repo (Fork)**
- **Pros:** Clean start, keep tax-demo intact
- **Cons:** Lose git history, duplicate work
- **Time:** 2-3 hours (just copy relevant files)

---

## My Recommendation

**Create new repo (Option B).** Here's why:

1. **Keep tax-demo intact** (it's your proof of concept)
2. **Clean git history** (professional from Day 1)
3. **Faster** (2-3 hours vs 8-12 hours)
4. **Less risky** (no chance of breaking tax-demo)
5. **Better for team** (clear separation)

**But if you want to convert this repo, I can do it. Just confirm:**

**Do you want to:**
- **A) Convert this repo** (transform tax-demo → vela-ops-squad)
- **B) Create new repo** (fork relevant files, clean start)

**Which approach do you prefer?**