# Agent Response Optimization Guide

## Overview
Best practices for making the tax document agent's responses more user-friendly, accurate, and actionable.

---

## Current Implementation

### What's Already Good:
✅ **Structured prompts** - System prompt includes context, examples, constraints  
✅ **Tool calling** - Agent uses Gateway tools for structured data  
✅ **Streaming responses** - Real-time feedback  
✅ **Memory** - 120-day conversation persistence  

### What Can Be Improved:
- Response formatting (markdown, tables, lists)
- Interactive clarification
- Confidence scores
- User feedback integration
- Personalization

---

## Best Practice #1: Structured Output Formatting

### Current:
```
Agent: "You have 5 clients. 2 complete, 1 at risk, 2 incomplete."
```

### Improved with Markdown:
```markdown
## Your Clients Summary

**Total:** 5 clients

### Status Breakdown:
- ✅ **Complete:** 2 clients (40%)
- ⚠️ **At Risk:** 1 client (20%)
- 🔄 **Incomplete:** 2 clients (40%)

### Action Required:
- **Urgent:** Contact at-risk client immediately
- **Follow-up:** Send reminders to 2 incomplete clients
```

### Implementation:
```python
# In agent system prompt, add:
**Response formatting:**
- Use markdown for structure (headers, lists, bold)
- Use emojis for visual cues (✅ ⚠️ 🔄 📧 📊)
- Break down complex information into sections
- Use tables for comparisons
- Use bullet points for lists
- Highlight action items with **bold**
```

---

## Best Practice #2: Confidence Scores & Reasoning

### Current:
```
Agent: "Mohamed has submitted his W-2."
```

### Improved with Confidence:
```
Agent: "Mohamed has submitted his W-2. ✅ (Verified: uploaded 2026-01-25)

**Confidence:** High (document found in S3 with metadata)
**Still needed:** Prior Year Tax Return
**Recommendation:** Send reminder in 3 days if not received
```

### Implementation:
```python
# Add to system prompt:
**When providing information:**
- State your confidence level (High/Medium/Low)
- Explain your reasoning
- Cite data sources (DynamoDB, S3, tool results)
- Suggest next actions
- Flag uncertainties
```

---

## Best Practice #3: Interactive Clarification

### Current:
```
User: "Send a reminder"
Agent: [Calls tool with default values, might be wrong client]
```

### Improved with Clarification:
```
User: "Send a reminder"
Agent: "I'd be happy to send a reminder! To make sure I send it to the right person:

**Which client?**
1. Mohamed Mohamud (at risk, 9 reminders sent)
2. John Smith (incomplete, 1 reminder sent)
3. Jane Doe (at risk, 2 reminders sent)

Or tell me the client's name."
```

### Implementation:
```python
# Add to system prompt:
**When information is ambiguous:**
- Ask clarifying questions before acting
- Provide options when multiple choices exist
- Confirm destructive actions (escalate, delete)
- Suggest the most likely option
- Make it easy to correct mistakes
```

---

## Best Practice #4: Contextual Responses

### Current:
```
User: "What's the status?"
Agent: "I need more information. Which client?"
```

### Improved with Context:
```
User: "What's the status?"
Agent: "I can check status for:

**Recent activity:**
- Mohamed Mohamud (you viewed 2 minutes ago)
- John Smith (reminder sent today)

**Or I can show:**
- All your clients (5 total)
- Only at-risk clients (1)
- Clients with recent uploads

What would you like to see?"
```

### Implementation:
```python
# Use AgentCore Memory to track:
- Recently viewed clients
- Recent actions taken
- User preferences
- Common queries

# Add to system prompt:
**Use conversation context:**
- Remember recently mentioned clients
- Reference previous actions in this session
- Suggest based on recent activity
- Learn user preferences over time
```

---

## Best Practice #5: Actionable Summaries

### Current:
```
Agent: "John Smith is at 33% complete. Missing W-2 and 1099-INT."
```

### Improved with Actions:
```
Agent: "## John Smith - Status Update

**Progress:** 33% complete (1 of 3 documents)

**Received:** ✅
- Prior Year Tax Return (uploaded 2026-01-20)

**Missing:** ❌
- W-2 from ABC Company
- 1099-INT from Chase Bank

**History:**
- Reminder #2 sent 5 days ago
- No response yet

**Recommended Actions:**
1. 🔴 **Send Reminder #3** (urgent - approaching escalation)
2. 📞 **Call client** if no response in 48 hours
3. 📧 **Send upload link** to make it easier

Would you like me to send reminder #3 now?"
```

### Implementation:
```python
# Add to system prompt:
**Always provide:**
1. Current status with visual indicators
2. Historical context
3. Recommended next actions (prioritized)
4. Easy way to take action
5. Timeline/urgency indicators
```

---

## Best Practice #6: Error Handling & Transparency

### Current:
```
Agent: "Error: Client not found"
```

### Improved with Transparency:
```
Agent: "❌ I couldn't find that client.

**What I checked:**
- Client database for name 'John Smth'
- Possible matches: John Smith, John Smythe

**Possible reasons:**
- Typo in name
- Client not yet added to system
- Client belongs to different accountant

**What you can do:**
1. Check spelling: Did you mean 'John Smith'?
2. View all clients to find the right one
3. Add new client if they don't exist

Would you like me to show all your clients?"
```

### Implementation:
```python
# Add to system prompt:
**When errors occur:**
- Explain what went wrong in plain language
- Suggest possible causes
- Provide actionable solutions
- Offer alternatives
- Never just say "error" without context
```

---

## Best Practice #7: Personalization

### Current:
```
Agent: "You have 5 clients."
```

### Improved with Personalization:
```
Agent: "Good morning! You have 5 clients.

**Since yesterday:**
- 📥 1 new upload (Mohamed's W-2)
- 📧 2 reminders sent
- ✅ 1 client completed

**Needs attention today:**
- Jane Doe (escalation in 1 day)

**Your typical workflow:**
- You usually check clients in the morning
- You prefer to send reminders in batches
- You like detailed status updates

Ready to review your at-risk clients?"
```

### Implementation:
```python
# Track in AgentCore Memory:
- Time of day preferences
- Communication style (brief vs detailed)
- Typical workflows
- Frequently asked questions

# Add to system prompt:
**Personalize responses:**
- Greet based on time of day
- Adapt detail level to user preference
- Highlight what's changed since last session
- Proactively suggest based on patterns
- Remember user's communication style
```

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Add markdown formatting to responses
2. ✅ Add emojis for visual cues
3. ✅ Structure responses with headers
4. ✅ Always provide next actions

### Phase 2: Enhanced UX (3-4 hours)
1. Add interactive clarification
2. Implement confidence scores
3. Add reasoning explanations
4. Improve error messages

### Phase 3: Personalization (1 week)
1. Track user preferences in memory
2. Learn communication patterns
3. Adapt response style
4. Proactive suggestions

---

## Prompt Engineering Template

```python
system_prompt = """
[Role & Purpose]
You are a Tax Document Collection Assistant...

[Context Awareness]
- You have access to user_id (accountant identifier)
- Use AgentCore Memory to remember preferences
- Track recent activity in conversation

[Response Format]
- Use markdown for structure
- Include emojis for visual cues (✅ ⚠️ 🔄 📧)
- Break into sections with headers
- Use bullet points and tables
- Highlight actions with **bold**

[Confidence & Reasoning]
- State confidence level when uncertain
- Explain your reasoning
- Cite data sources
- Flag assumptions

[Clarification]
- Ask questions when ambiguous
- Provide options when multiple choices
- Confirm before destructive actions
- Make corrections easy

[Actionability]
- Always suggest next steps
- Prioritize recommendations
- Make actions easy to execute
- Provide context for decisions

[Error Handling]
- Explain errors in plain language
- Suggest causes and solutions
- Offer alternatives
- Never just say "error"

[Personalization]
- Adapt to user's communication style
- Remember preferences
- Highlight changes since last session
- Proactive based on patterns

[Examples]
[Include 5-10 example interactions showing best practices]
"""
```

---

## Measuring Success

### Metrics to Track:
- User satisfaction ratings (via feedback API)
- Task completion rate
- Clarification request frequency
- Error rate
- Response time
- User retention

### A/B Testing:
- Test different prompt variations
- Compare response formats
- Measure user engagement
- Optimize based on data

---

## Quick Implementation

**Update system prompt now:**
1. Add markdown formatting instructions
2. Add emoji usage guidelines
3. Add "always provide next actions" rule
4. Add clarification examples

**Time:** 30 minutes  
**Impact:** Immediate improvement in response quality  
**Effort:** Low (just prompt engineering)

---

**Status:** Implementation guide ready  
**Next Step:** Update agent system prompt with best practices  
**Expected Improvement:** 20-30% better user satisfaction
