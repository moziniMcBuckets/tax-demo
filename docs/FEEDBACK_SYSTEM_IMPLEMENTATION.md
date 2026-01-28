# Feedback System Implementation Plan

## Overview
Implement user feedback collection to improve agent responses and track user satisfaction.

---

## Architecture

```
Chat Interface → User rates response (👍/👎) → Feedback API → DynamoDB → Analytics Dashboard
```

---

## Components

### 1. Feedback UI in Chat (1 hour)

**Add to ChatMessage component:**
```typescript
// frontend/src/components/chat/ChatMessage.tsx

{message.role === 'assistant' && (
  <div className="flex gap-2 mt-2">
    <Button
      size="sm"
      variant="ghost"
      onClick={() => handleFeedback('positive')}
    >
      👍 Helpful
    </Button>
    <Button
      size="sm"
      variant="ghost"
      onClick={() => handleFeedback('negative')}
    >
      👎 Not Helpful
    </Button>
  </div>
)}
```

**Feedback dialog for comments:**
```typescript
{showFeedbackDialog && (
  <Dialog>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Help us improve</DialogTitle>
        <DialogDescription>
          What could have been better about this response?
        </DialogDescription>
      </DialogHeader>
      <textarea
        placeholder="Optional: Tell us more..."
        value={feedbackComment}
        onChange={(e) => setFeedbackComment(e.target.value)}
      />
      <DialogFooter>
        <Button onClick={submitFeedback}>Submit</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
)}
```

### 2. Feedback API (Already Exists)

**Endpoint:** `POST /feedback`

**Request:**
```json
{
  "sessionId": "session-123",
  "message": "Agent's response text",
  "feedbackType": "positive" | "negative",
  "comment": "Optional explanation"
}
```

**Response:**
```json
{
  "success": true,
  "feedbackId": "fb-123"
}
```

### 3. Analytics Dashboard (2 hours)

**New tab in main app:**
```typescript
// frontend/src/components/analytics/FeedbackDashboard.tsx

export function FeedbackDashboard() {
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    fetch(`${apiUrl}/feedback/stats`)
      .then(res => res.json())
      .then(data => setStats(data));
  }, []);
  
  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>User Satisfaction</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <h3 className="text-3xl font-bold text-green-600">
                {stats.positive_rate}%
              </h3>
              <p className="text-sm text-gray-500">Positive Feedback</p>
            </div>
            <div>
              <h3 className="text-3xl font-bold">
                {stats.total_responses}
              </h3>
              <p className="text-sm text-gray-500">Total Responses</p>
            </div>
            <div>
              <h3 className="text-3xl font-bold text-red-600">
                {stats.negative_count}
              </h3>
              <p className="text-sm text-gray-500">Needs Improvement</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Recent Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          {stats.recent_feedback.map(fb => (
            <div key={fb.id} className="border-b py-3">
              <div className="flex items-center gap-2">
                {fb.type === 'positive' ? '👍' : '👎'}
                <span className="text-sm text-gray-500">
                  {new Date(fb.timestamp).toLocaleString()}
                </span>
              </div>
              <p className="text-sm mt-1">{fb.message.substring(0, 100)}...</p>
              {fb.comment && (
                <p className="text-sm text-gray-600 mt-1 italic">
                  "{fb.comment}"
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4. Analytics Lambda (1 hour)

**Create:** `infra-cdk/lambdas/feedback_analytics/index.py`

```python
def get_feedback_stats(accountant_id: str, days: int = 30):
    """Get feedback statistics."""
    table = dynamodb.Table('tax-agent-feedback')
    
    # Query recent feedback
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    response = table.query(
        IndexName='feedbackType-timestamp-index',
        KeyConditionExpression='feedbackType = :type AND timestamp > :cutoff',
        ExpressionAttributeValues={':type': 'positive', ':cutoff': cutoff}
    )
    
    positive = len(response['Items'])
    
    # Get negative feedback
    response = table.query(
        IndexName='feedbackType-timestamp-index',
        KeyConditionExpression='feedbackType = :type AND timestamp > :cutoff',
        ExpressionAttributeValues={':type': 'negative', ':cutoff': cutoff}
    )
    
    negative = len(response['Items'])
    total = positive + negative
    
    return {
        'positive_count': positive,
        'negative_count': negative,
        'total_responses': total,
        'positive_rate': round((positive / total * 100) if total > 0 else 0, 1),
        'period_days': days
    }
```

---

## Benefits

### For Product Team:
- 📊 Track user satisfaction
- 🎯 Identify problem areas
- 📈 Measure improvements
- 🔍 Find edge cases

### For Users:
- 🗣️ Voice heard
- 🚀 Product improves
- 💡 Influence features
- ✅ Better experience

---

## Implementation Timeline

**Week 1:**
- Add feedback buttons to chat
- Connect to existing API
- Test feedback flow

**Week 2:**
- Build analytics dashboard
- Create stats Lambda
- Add to main navigation

**Week 3:**
- Monitor feedback
- Analyze patterns
- Improve prompts based on data

---

## Metrics to Track

1. **Satisfaction Rate** - % positive feedback
2. **Response Volume** - Total feedback received
3. **Common Issues** - Patterns in negative feedback
4. **Improvement Trends** - Satisfaction over time
5. **Feature Requests** - What users ask for

---

## Success Criteria

- ✅ 80%+ positive feedback rate
- ✅ 50%+ of users provide feedback
- ✅ Clear patterns identified
- ✅ Actionable improvements found
- ✅ Satisfaction trending up

---

**Status:** Implementation plan ready  
**Priority:** Medium (nice-to-have for beta)  
**Effort:** 4-5 hours  
**Value:** Continuous improvement, user insights
