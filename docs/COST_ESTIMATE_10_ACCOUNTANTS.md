# Cost Estimate: 10 Accountants (Multi-Tenant)

## Scenario

**10 accountants**, each managing **50 clients** during tax season (January - April)

**ASSUMPTIONS - Usage per accountant per month**:
- 100 agent conversations (chat queries) ⚠️ ESTIMATED
- 150 upload links sent (3 per client) ⚠️ ESTIMATED
- 300 reminder emails (6 per client) ⚠️ ESTIMATED
- 50 SMS messages (if enabled) ⚠️ ESTIMATED
- 500 Gateway tool calls (status checks, document checks) ⚠️ ESTIMATED

**Note**: These are conservative estimates. Actual usage will vary based on:
- How often accountants use the chat vs UI
- Client responsiveness (more reminders = higher cost)
- SMS adoption rate
- Automation level

## Cost Breakdown

### 1. AgentCore Runtime

**Pricing**: $0.003 per invocation (CPU + Memory)

**Usage**:
- 10 accountants × 100 conversations = 1,000 invocations/month

**Cost**: 1,000 × $0.003 = **$3.00/month**

### 2. AgentCore Gateway

**Pricing**: 
- SearchToolIndex: $0.02 per 100 tools
- InvokeTool: $5 per million calls

**Usage**:
- 7 tools indexed: $0.02
- 10 accountants × 500 tool calls = 5,000 calls/month

**Cost**: $0.02 + (5,000 × $5/1M) = **$0.05/month**

### 3. AgentCore Memory

**Pricing**:
- Short-term events: $0.25 per 1,000 events
- Long-term storage: $0.75 per 1,000 records
- Retrieval: $0.50 per 1,000 retrievals

**Usage**:
- 1,000 conversation events (2 per conversation)
- 100 long-term memories stored
- 1,000 memory retrievals

**Cost**: 
- Events: 1,000 × $0.25/1K = $0.25
- Storage: 100 × $0.75/1K = $0.08
- Retrieval: 1,000 × $0.50/1K = $0.50
- **Total: $0.83/month**

### 4. Lambda Functions

**Pricing**: $0.20 per 1M requests + $0.0000166667 per GB-second

**Usage**:
- 13 Lambda functions
- 10 accountants × 1,000 operations = 10,000 invocations/month
- Average 512MB, 1 second duration

**Cost**:
- Requests: 10,000 × $0.20/1M = $0.002
- Compute: 10,000 × 0.5GB × 1s × $0.0000166667 = $0.08
- **Total: $0.08/month**

### 5. DynamoDB

**Pricing**: $1.25 per million write requests, $0.25 per million read requests

**Usage**:
- 10 accountants × 1,000 operations = 10,000 writes
- 50,000 reads (status checks, queries)

**Cost**:
- Writes: 10,000 × $1.25/1M = $0.01
- Reads: 50,000 × $0.25/1M = $0.01
- **Total: $0.02/month**

### 6. S3 Storage

**Pricing**: $0.023 per GB/month + $0.0004 per 1,000 PUT requests

**Usage**:
- 500 clients × 5 documents × 1MB = 2.5GB storage
- 2,500 uploads

**Cost**:
- Storage: 2.5GB × $0.023 = $0.06
- Requests: 2,500 × $0.0004/1K = $0.001
- **Total: $0.06/month**

### 7. SES (Email)

**Pricing**: $0.10 per 1,000 emails

**Usage**:
- 10 accountants × 450 emails = 4,500 emails/month

**Cost**: 4,500 × $0.10/1K = **$0.45/month**

### 8. SNS (SMS) - Optional

**Pricing**: $0.00645 per SMS (US)

**Usage**:
- 10 accountants × 50 SMS = 500 SMS/month

**Cost**: 500 × $0.00645 = **$3.23/month**

### 9. API Gateway

**Pricing**: $3.50 per million requests

**Usage**:
- 10 accountants × 1,000 API calls = 10,000 calls/month

**Cost**: 10,000 × $3.50/1M = **$0.04/month**

### 10. Amplify Hosting

**Pricing**: $0.15 per GB served + $0.01 per build minute

**Usage**:
- 1GB served/month
- 10 builds × 2 minutes

**Cost**: 
- Serving: 1GB × $0.15 = $0.15
- Builds: 10 × 2 × $0.01 = $0.20
- **Total: $0.35/month**

### 11. Cognito

**Pricing**: Free for first 50,000 MAUs

**Usage**: 10 accountants (well under limit)

**Cost**: **$0.00/month**

---

## Total Monthly Cost

| Component | Cost | % of Total |
|-----------|------|------------|
| AgentCore Runtime | $3.00 | 38% |
| AgentCore Memory | $0.83 | 10% |
| SMS (optional) | $3.23 | 41% |
| SES (email) | $0.45 | 6% |
| Amplify | $0.35 | 4% |
| Lambda | $0.08 | 1% |
| S3 | $0.06 | <1% |
| Gateway | $0.05 | <1% |
| API Gateway | $0.04 | <1% |
| DynamoDB | $0.02 | <1% |
| Cognito | $0.00 | 0% |
| **TOTAL (with SMS)** | **$8.11** | **100%** |
| **TOTAL (email only)** | **$4.88** | **100%** |

---

## Per-Tenant Cost

**With SMS**: $8.11 / 10 = **$0.81 per accountant/month**

**Email only**: $4.88 / 10 = **$0.49 per accountant/month**

---

## Scaling Estimates

### 50 Accountants (2,500 clients)

| Component | Cost |
|-----------|------|
| AgentCore Runtime | $15.00 |
| AgentCore Memory | $4.15 |
| SMS (optional) | $16.15 |
| SES | $2.25 |
| Other services | $2.50 |
| **Total (with SMS)** | **$40.05** |
| **Total (email only)** | **$23.90** |

**Per tenant**: $0.80/month (with SMS) or $0.48/month (email only)

### 100 Accountants (5,000 clients)

| Component | Cost |
|-----------|------|
| AgentCore Runtime | $30.00 |
| AgentCore Memory | $8.30 |
| SMS (optional) | $32.30 |
| SES | $4.50 |
| Other services | $5.00 |
| **Total (with SMS)** | **$80.10** |
| **Total (email only)** | **$47.80** |

**Per tenant**: $0.80/month (with SMS) or $0.48/month (email only)

---

## Pricing Strategy Recommendations

### Option 1: Cost-Plus Pricing (50% margin)

**Email only**:
- Cost: $0.49/accountant
- Price: $0.75/accountant/month
- Margin: $0.26 (53%)

**With SMS**:
- Cost: $0.81/accountant
- Price: $1.25/accountant/month
- Margin: $0.44 (54%)

### Option 2: Tiered Subscription

| Tier | Clients | Operations | Price | Cost | Margin |
|------|---------|------------|-------|------|--------|
| Starter | 10 | 100/month | $5 | $0.10 | $4.90 (98%) |
| Professional | 50 | 500/month | $15 | $0.49 | $14.51 (97%) |
| Enterprise | 200 | 2000/month | $50 | $1.96 | $48.04 (96%) |

### Option 3: Pay-Per-Use

| Operation | AWS Cost | Your Price | Margin |
|-----------|----------|------------|--------|
| Agent query | $0.003 | $0.01 | 233% |
| Email sent | $0.0001 | $0.001 | 900% |
| SMS sent | $0.00645 | $0.02 | 210% |
| Upload link | $0.0001 | $0.001 | 900% |

---

## Cost Optimization Tips

### 1. Reduce Runtime Costs (38% of total)
- Use prompt caching (reduces tokens by 90%)
- Batch operations where possible
- Use cheaper models for simple tasks

### 2. Reduce SMS Costs (41% of total)
- Make SMS opt-in only
- Use email as primary channel
- Send SMS only for urgent reminders

### 3. Reduce Memory Costs (10% of total)
- Set shorter event expiry (7 days vs 30 days)
- Use short-term memory only (no long-term extraction)
- Clear old sessions periodically

### 4. Optimize Gateway Calls
- Cache tool results
- Batch status checks
- Reduce unnecessary tool invocations

---

## Free Tier Benefits

**First 12 months** (new AWS accounts):
- Lambda: 1M requests/month free
- DynamoDB: 25GB storage + 25 WCU/RCU free
- S3: 5GB storage free
- SES: 62,000 emails/month free (if sending from EC2)

**Always free**:
- Cognito: 50,000 MAUs free
- CloudWatch: 10 custom metrics free

**AgentCore Free Tier**:
- New customers: $200 in credits
- Covers ~66,000 Runtime invocations
- Or ~40M Gateway calls
- Or ~800K Memory events

---

## Summary

**10 accountants managing 500 clients**:
- **$4.88/month** (email only) = **$0.49 per accountant**
- **$8.11/month** (with SMS) = **$0.81 per accountant**

**Recommended pricing**:
- **$15/month per accountant** (Professional tier)
- Covers up to 50 clients and 500 operations
- 97% margin
- Competitive with market rates

**Break-even**: 1 accountant at $15/month covers costs for 30 accountants

The application is **extremely cost-effective** for multi-tenant SaaS! 🎯

---

## How to Get Actual Costs

### Real-Time Usage Tracking

**Your application tracks actual usage per tenant**:

```bash
# View actual costs for a specific accountant
python3 scripts/get-tenant-costs.py --accountant-id YOUR_COGNITO_SUB

# View all tenants
python3 scripts/get-tenant-costs.py --month 2026-01
```

This shows:
- Actual operations performed
- Real costs incurred
- No assumptions needed

### AWS Cost Explorer (24-48 hour delay)

```bash
# View AWS infrastructure costs
python3 scripts/get-costs.py --month 2026-01
```

This shows:
- Actual AWS bills by service
- Tagged resources only
- Infrastructure costs (not per-tenant)

### Recommended Approach

1. **Run for 1 month** with real usage
2. **Check actual costs** using the scripts above
3. **Calculate per-tenant average** from real data
4. **Set pricing** based on actual costs + desired margin

**Don't rely on estimates** - use your actual usage data from the tracking table!

---

## Pricing Verification

**All pricing rates verified from**:
- [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/) - January 2026
- [Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [SES Pricing](https://aws.amazon.com/ses/pricing/)
- [SNS Pricing](https://aws.amazon.com/sns/pricing/)

**Usage volumes are estimates** - your actual usage may be higher or lower.

---

**Calculation Date**: January 29, 2026
**Pricing Source**: AWS Official Pricing Pages
**Usage Assumptions**: Conservative estimates for tax season
**Recommendation**: Monitor actual usage for 30 days before setting prices
