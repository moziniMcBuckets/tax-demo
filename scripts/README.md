# Vela Operations Squad - Scripts

**Purpose:** Testing, deployment, and utility scripts for Operations Squad

---

## Testing Scripts

### **test-operations-squad.py** (To be created - Week 4)
Test complete Operations Squad end-to-end flow.

**Usage:**
```bash
python3 scripts/test-operations-squad.py
```

### **test-lead-response.py** (To be created - Week 1)
Test Lead Response Agent and tools.

### **test-scheduler.py** (To be created - Week 2)
Test Scheduler Agent and tools.

### **test-invoice.py** (To be created - Week 3)
Test Invoice Agent and tools.

### **test-gateway.py** (Keep)
Test AgentCore Gateway connectivity.

### **test-memory.py** (Keep)
Test AgentCore Memory integration.

### **test-agent.py** (Keep, will update)
Generic agent testing script.

### **test-all-gateway-tools.py** (Keep, will update)
Test all gateway tools for Operations Squad.

---

## Deployment Scripts

### **deploy-frontend.py** (Keep, will update)
Deploy frontend to AWS Amplify.

**Usage:**
```bash
python3 scripts/deploy-frontend.py
```

### **add-lambda-permissions.py** (Keep)
Add IAM permissions to Lambda functions.

### **configure-s3-cors.py** (Keep)
Configure S3 CORS for document uploads.

---

## Utility Scripts

### **seed-operations-test-data.py** (To be created - Week 1)
Seed test data for Operations Squad.

**Creates:**
- 5 test leads
- 3 test technicians
- Sample appointments
- Sample invoices

**Usage:**
```bash
python3 scripts/seed-operations-test-data.py
```

### **get-costs.py** (Keep)
Calculate AWS infrastructure costs.

### **generate-architecture-diagram.py** (Keep, will update)
Generate architecture diagram for Operations Squad.

### **utils.py** (Keep)
Shared utility functions.

---

## Conversion Scripts

### **convert_to_vela.sh** (Keep)
One-time conversion script (already run).

---

## Dependencies

See `requirements.txt` for Python dependencies.

**Install:**
```bash
pip install -r scripts/requirements.txt
```

---

## Next Steps

**Week 1:**
- Create test-lead-response.py
- Create seed-operations-test-data.py
- Update test-agent.py for Operations Squad

**Week 2:**
- Create test-scheduler.py

**Week 3:**
- Create test-invoice.py

**Week 4:**
- Create test-operations-squad.py (end-to-end)
- Update test-all-gateway-tools.py

---

**Status:** Scripts folder cleaned up and ready for Operations Squad development.
