# Real-Time AWS Billing Implementation Plan

## Overview
Integrate actual AWS costs from Cost and Usage Reports (CUR) for accurate per-tenant billing.

---

## Architecture

```
AWS Services → Cost and Usage Reports → S3 → EventBridge → Lambda → Process CUR → DynamoDB (usage table)
                                                                                    ↓
                                                                            Aggregate by accountant_id
                                                                                    ↓
                                                                            Billing API → Frontend Dashboard
```

---

## Components

### 1. Cost and Usage Reports (CUR)
**What:** AWS generates detailed billing data every hour  
**Format:** Parquet or CSV files in S3  
**Granularity:** Per-resource, per-hour costs  
**Includes:** Service, operation, resource tags, actual costs  

### 2. Cost Allocation Tags
**Required tags on all resources:**
- `accountant_id` - For tenant attribution
- `application` - "tax-demo"
- `environment` - "production"
- `cost_center` - For internal tracking

### 3. CUR Processing Lambda
**Triggers:** S3 event when new CUR file arrives  
**Process:** Parse CUR, extract costs by accountant_id  
**Output:** Update usage table with actual costs  

### 4. Billing Reconciliation
**Compare:** Estimated costs vs actual AWS costs  
**Adjust:** Update pricing model if needed  
**Report:** Show variance to accountants  

---

## Implementation Steps

### Phase 1: Enable CUR (30 min)

**1.1 Create CUR in AWS Console:**
```
AWS Console → Billing → Cost & Usage Reports → Create Report

Settings:
- Report name: tax-demo-cur
- Time granularity: Hourly
- Report versioning: Overwrite existing
- Enable resource IDs: Yes
- Data refresh: Yes
- Compression: Parquet
- S3 bucket: Create new or use existing
```

**1.2 Add to CDK:**
```typescript
// Create S3 bucket for CUR
const curBucket = new s3.Bucket(this, 'CurBucket', {
  bucketName: `${config.stack_name_base}-cur-${this.account}`,
  removalPolicy: cdk.RemovalPolicy.RETAIN,
  lifecycleRules: [{
    expiration: cdk.Duration.days(90),  // Keep 90 days
  }],
});

// CUR configuration (via CloudFormation)
new cdk.CfnResource(this, 'CostAndUsageReport', {
  type: 'AWS::CUR::ReportDefinition',
  properties: {
    ReportName: `${config.stack_name_base}-cur`,
    TimeUnit: 'HOURLY',
    Format: 'Parquet',
    Compression: 'Parquet',
    S3Bucket: curBucket.bucketName,
    S3Prefix: 'cur',
    S3Region: this.region,
    RefreshClosedReports: true,
    ReportVersioning: 'OVERWRITE_REPORT',
  }
});
```

---

### Phase 2: Add Cost Allocation Tags (1 hour)

**2.1 Tag all resources in CDK:**
```typescript
// In backend-stack.ts constructor
cdk.Tags.of(this).add('application', 'tax-demo');
cdk.Tags.of(this).add('environment', 'production');

// Tag resources with accountant_id dynamically
// This requires custom tagging logic per resource
```

**2.2 Activate tags in AWS:**
```bash
# Activate cost allocation tags
aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status \
    TagKey=accountant_id,Status=Active \
    TagKey=application,Status=Active
```

**Challenge:** Most resources (Lambda, DynamoDB) are shared across tenants.  
**Solution:** Use CloudWatch Logs Insights to attribute usage, not resource tags.

---

### Phase 3: CUR Processing Lambda (2 hours)

**3.1 Create Lambda:**
```python
# infra-cdk/lambdas/cur_processor/index.py

import boto3
import pandas as pd
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def process_cur_file(bucket: str, key: str):
    """Process CUR Parquet file and extract costs."""
    
    # Download CUR file from S3
    obj = s3.get_object(Bucket=bucket, Key=key)
    
    # Read Parquet file
    df = pd.read_parquet(obj['Body'])
    
    # Filter for tax-demo resources
    df = df[df['resource_tags_user_application'] == 'tax-demo']
    
    # Group by accountant_id and service
    grouped = df.groupby([
        'resource_tags_user_accountant_id',
        'product_product_name',
        'line_item_usage_start_date'
    ]).agg({
        'line_item_unblended_cost': 'sum',
        'line_item_usage_amount': 'sum'
    })
    
    # Update usage table with actual costs
    usage_table = dynamodb.Table('tax-agent-usage')
    
    for (accountant_id, service, date), row in grouped.iterrows():
        if pd.isna(accountant_id):
            continue
            
        usage_table.put_item(Item={
            'accountant_id': accountant_id,
            'timestamp': date.isoformat(),
            'month': date.strftime('%Y-%m'),
            'operation': 'aws_service_usage',
            'resource_type': service.lower().replace(' ', '_'),
            'quantity': Decimal(str(row['line_item_usage_amount'])),
            'unit_cost': Decimal('0'),  # Calculated from total
            'estimated_cost': Decimal(str(row['line_item_unblended_cost'])),
            'source': 'cur',  # Mark as actual cost
            'actual_cost': True
        })
```

**3.2 Add S3 trigger:**
```typescript
curBucket.addEventNotification(
  s3.EventType.OBJECT_CREATED,
  new s3n.LambdaDestination(curProcessorLambda),
  { prefix: 'cur/', suffix: '.parquet' }
);
```

**3.3 Dependencies:**
```
boto3
pandas
pyarrow  # For Parquet
```

---

### Phase 4: Attribution Logic (3 hours)

**Challenge:** Shared resources (Lambda, DynamoDB) serve multiple tenants.

**Solution: Usage-based attribution**

**4.1 Lambda costs:**
```python
# Parse CloudWatch Logs Insights
# Query: fields @timestamp, @message | filter @message like /accountant_id/

# Calculate:
# - Invocations per accountant
# - Duration per accountant
# - Memory used per accountant
# Cost = (invocations × $0.20/1M) + (GB-seconds × $0.0000166667)
```

**4.2 DynamoDB costs:**
```python
# Track read/write units per accountant
# Use CloudWatch metrics with dimensions

# Cost = (RCU × $0.25/million) + (WCU × $1.25/million)
```

**4.3 S3 costs:**
```python
# Track storage per client folder
# Client folder → accountant_id mapping

# Cost = (GB × $0.023/month) + (requests × pricing)
```

**4.4 AgentCore costs:**
```python
# Parse AgentCore logs for user_id (accountant_id)
# Track invocations and tool calls per accountant

# Cost = (sessions × $0.003) + (tool calls × $0.0001)
```

---

### Phase 5: Billing Dashboard (2 hours)

**5.1 Create UI component:**
```typescript
// frontend/src/components/billing/UsageDashboard.tsx

export function UsageDashboard() {
  const [usage, setUsage] = useState(null);
  
  useEffect(() => {
    fetch(`${apiUrl}/billing?month=2026-01`)
      .then(res => res.json())
      .then(data => setUsage(data));
  }, []);
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your Usage & Costs</CardTitle>
        <CardDescription>January 2026</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <h3>Total Cost: ${usage.total_cost}</h3>
          </div>
          
          <div>
            <h4>Breakdown:</h4>
            {Object.entries(usage.usage_by_type).map(([type, data]) => (
              <div key={type}>
                {type}: {data.quantity} × ${data.unit_cost} = ${data.cost}
              </div>
            ))}
          </div>
          
          <div>
            <h4>Actual AWS Costs (from CUR):</h4>
            {/* Show actual costs when available */}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

**5.2 Add to main navigation:**
- New tab: "Billing"
- Shows current month usage
- Historical data
- Export to CSV

---

### Phase 6: Cost Reconciliation (1 hour)

**6.1 Compare estimated vs actual:**
```python
def reconcile_costs(accountant_id: str, month: str):
    # Get estimated costs (from usage tracking)
    estimated = get_estimated_costs(accountant_id, month)
    
    # Get actual costs (from CUR)
    actual = get_actual_costs_from_cur(accountant_id, month)
    
    # Calculate variance
    variance = actual - estimated
    variance_pct = (variance / actual) * 100 if actual > 0 else 0
    
    return {
        'estimated': estimated,
        'actual': actual,
        'variance': variance,
        'variance_pct': variance_pct
    }
```

**6.2 Adjust pricing:**
If variance > 10%, update pricing constants.

---

## Challenges & Solutions

### Challenge 1: Shared Resources
**Problem:** Lambda serves multiple tenants, can't tag per tenant  
**Solution:** Parse CloudWatch Logs to attribute usage

### Challenge 2: 24-Hour Delay
**Problem:** CUR data is delayed  
**Solution:** Use estimates for real-time, reconcile with CUR daily

### Challenge 3: Complex Attribution
**Problem:** Hard to split shared costs  
**Solution:** Use usage metrics (invocations, storage) as proxy

### Challenge 4: Tag Propagation
**Problem:** Not all resources support tags  
**Solution:** Use CloudWatch metrics and logs for attribution

---

## Simplified Alternative: Cost Explorer API

**Easier implementation:**
```python
# Daily job to fetch costs
ce = boto3.client('ce')

response = ce.get_cost_and_usage(
    TimePeriod={'Start': '2026-01-01', 'End': '2026-01-31'},
    Granularity='DAILY',
    Metrics=['UnblendedCost'],
    GroupBy=[{'Type': 'TAG', 'Key': 'accountant_id'}]
)

# Store in usage table with source='cost_explorer'
```

**Pros:**
- ✅ Simpler than CUR
- ✅ API-based
- ✅ Actual AWS costs

**Cons:**
- ❌ Still 24-hour delay
- ❌ Requires tags on resources
- ❌ Less granular than CUR

---

## Recommended Approach

**For Beta:**
1. ✅ Use current estimate-based tracking (already implemented)
2. ✅ Show usage metrics to users
3. ✅ Manually reconcile with AWS bill monthly

**For Production:**
1. Implement Cost Explorer API integration (simpler)
2. Daily job to fetch actual costs
3. Update usage table with actual costs
4. Show both estimated and actual in UI
5. Reconcile and adjust estimates

**For Enterprise:**
1. Full CUR implementation
2. Real-time cost attribution
3. Automated invoicing
4. Chargeback reports

---

## Implementation Timeline

**Phase 1: Cost Explorer (1 week)**
- Enable Cost Explorer API
- Create daily sync Lambda
- Update billing API
- Add actual costs to UI

**Phase 2: CUR (2-3 weeks)**
- Enable CUR
- Build CUR processor
- Implement attribution logic
- Create reconciliation reports

**Phase 3: Automation (1 week)**
- Automated invoicing
- Stripe integration
- Payment processing
- Dunning workflows

---

## Cost Impact

**Cost Explorer API:**
- $0.01 per API request
- ~30 requests/month = $0.30/month
- Negligible

**CUR:**
- Free (AWS service)
- S3 storage: ~$0.50/month
- Processing: ~$0.10/month
- Total: ~$0.60/month

**ROI:** Accurate billing worth the cost!

---

**Status:** Implementation plan ready  
**Priority:** Medium (estimates work for beta)  
**Effort:** 1-3 weeks depending on approach  
**Value:** Accurate billing, customer trust, automated invoicing
