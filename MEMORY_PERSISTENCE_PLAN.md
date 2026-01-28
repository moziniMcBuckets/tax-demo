# Memory Persistence Fix - Implementation Plan

## Problem Analysis

### Current Behavior
1. User chats with agent → Session ID generated (e.g., `abc-123`)
2. Agent stores conversation in AgentCore Memory with session ID
3. User navigates to Dashboard → ChatInterface component unmounts
4. User returns to Chat → ChatInterface remounts with NEW session ID (e.g., `xyz-789`)
5. Agent can't find previous conversation (different session ID)
6. **Result**: Chat history appears lost

### Root Cause

**File**: `frontend/src/components/chat/ChatInterface.tsx` (Line 15)
```typescript
const [sessionId] = useState(() => generateSessionId())
```

The session ID is stored in component state, which is lost when the component unmounts.

### Why Memory IS Working

✅ AgentCore Memory is properly configured in the agent
✅ Memory is storing conversations correctly
✅ Agent can retrieve conversations by session ID
✅ The issue is ONLY in the frontend session management

## Solution: Persist Session ID

### Option 1: localStorage (Recommended)

**Pros**:
- Persists across page refreshes
- Persists across navigation
- Simple to implement
- Works offline

**Cons**:
- Cleared when user clears browser data
- Not shared across devices

### Option 2: Global Context

**Pros**:
- Centralized state management
- Easy to access from anywhere
- Can combine with localStorage

**Cons**:
- Lost on page refresh (unless combined with localStorage)

### Option 3: URL Parameter

**Pros**:
- Shareable sessions
- Visible to user

**Cons**:
- Clutters URL
- Can be accidentally changed

**Recommendation**: Use localStorage + Global Context for best UX.

## Implementation Plan

### Phase 1: Session Persistence (30 minutes)

#### 1.1 Create Session Manager Utility
**File**: `frontend/src/lib/sessionManager.ts` (NEW)

```typescript
/**
 * Session Manager
 * 
 * Manages chat session persistence across navigation and page refreshes.
 * Uses localStorage to store session ID per user.
 */

const SESSION_STORAGE_KEY = 'tax-agent-session-id';
const SESSION_EXPIRY_DAYS = 7; // Sessions expire after 7 days

interface SessionData {
  sessionId: string;
  userId: string;
  createdAt: string;
  lastAccessedAt: string;
}

export function getOrCreateSession(userId: string): string {
  // Try to load existing session
  const stored = localStorage.getItem(SESSION_STORAGE_KEY);
  
  if (stored) {
    try {
      const data: SessionData = JSON.parse(stored);
      
      // Check if session belongs to current user
      if (data.userId === userId) {
        // Check if session is still valid (not expired)
        const createdAt = new Date(data.createdAt);
        const now = new Date();
        const daysSinceCreation = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60 * 24);
        
        if (daysSinceCreation < SESSION_EXPIRY_DAYS) {
          // Update last accessed time
          data.lastAccessedAt = now.toISOString();
          localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(data));
          
          console.log(`Restored session: ${data.sessionId}`);
          return data.sessionId;
        } else {
          console.log('Session expired, creating new one');
        }
      } else {
        console.log('Session belongs to different user, creating new one');
      }
    } catch (e) {
      console.error('Error parsing stored session:', e);
    }
  }
  
  // Create new session
  const sessionId = crypto.randomUUID();
  const sessionData: SessionData = {
    sessionId,
    userId,
    createdAt: new Date().toISOString(),
    lastAccessedAt: new Date().toISOString()
  };
  
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
  console.log(`Created new session: ${sessionId}`);
  
  return sessionId;
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  console.log('Session cleared');
}

export function startNewSession(userId: string): string {
  clearSession();
  return getOrCreateSession(userId);
}
```

#### 1.2 Update ChatInterface Component
**File**: `frontend/src/components/chat/ChatInterface.tsx`

Change from:
```typescript
const [sessionId] = useState(() => generateSessionId())
```

To:
```typescript
import { getOrCreateSession, startNewSession } from '@/lib/sessionManager';

const auth = useAuth();
const userId = auth.user?.profile?.sub;

const [sessionId, setSessionId] = useState<string>(() => {
  if (userId) {
    return getOrCreateSession(userId);
  }
  return generateSessionId(); // Fallback
});

// Update session when user logs in
useEffect(() => {
  if (userId) {
    const persistedSessionId = getOrCreateSession(userId);
    setSessionId(persistedSessionId);
  }
}, [userId]);
```

#### 1.3 Update "New Chat" Button
**File**: `frontend/src/components/chat/ChatHeader.tsx`

Update `onNewChat` to create new session:
```typescript
const handleNewChat = () => {
  const userId = auth.user?.profile?.sub;
  if (userId) {
    const newSessionId = startNewSession(userId);
    setSessionId(newSessionId);
  }
  setMessages([]);
  setInput('');
};
```

### Phase 2: Session UI Indicators (15 minutes)

#### 2.1 Add Session Info Display
**File**: `frontend/src/components/chat/ChatHeader.tsx`

Add session indicator:
```typescript
<div className="text-xs text-gray-500">
  Session: {sessionId.substring(0, 8)}...
  <button onClick={copySessionId}>Copy</button>
</div>
```

#### 2.2 Add Session Age Indicator
Show how old the current session is:
```typescript
<div className="text-xs text-gray-500">
  Session started: {formatSessionAge(sessionCreatedAt)}
</div>
```

### Phase 3: Testing (15 minutes)

#### Test 1: Navigation Persistence
1. Start chat, send message
2. Navigate to Dashboard
3. Return to Chat
4. **Expected**: Previous messages visible, same session ID

#### Test 2: Page Refresh
1. Start chat, send message
2. Refresh page (F5)
3. **Expected**: Previous messages visible, same session ID

#### Test 3: New Chat
1. Click "New Chat" button
2. **Expected**: Messages cleared, NEW session ID generated

#### Test 4: Multi-User
1. Log in as User A, chat
2. Log out
3. Log in as User B, chat
4. **Expected**: User B gets their own session, not User A's

#### Test 5: Session Expiry
1. Manually set session createdAt to 8 days ago
2. Refresh page
3. **Expected**: New session created (old one expired)

### Phase 4: Memory Verification (10 minutes)

#### Verify Memory is Working
```bash
# Check if memory resource exists
aws bedrock-agentcore list-memories --region us-west-2

# Get memory details
aws bedrock-agentcore get-memory --memory-id <MEMORY_ID> --region us-west-2

# Check if events are being stored
aws bedrock-agentcore list-events \
  --memory-id <MEMORY_ID> \
  --actor-id <USER_ID> \
  --session-id <SESSION_ID> \
  --region us-west-2
```

## Implementation Summary

### Files to Modify
1. ✅ `frontend/src/lib/sessionManager.ts` (NEW)
2. ✅ `frontend/src/components/chat/ChatInterface.tsx` (UPDATE)
3. ✅ `frontend/src/components/chat/ChatHeader.tsx` (UPDATE - optional)

### Changes Required
- Create session manager utility
- Update ChatInterface to use persistent session
- Update New Chat button to create new session
- Add session indicators (optional)

### Estimated Time
- Session persistence: 30 minutes
- UI indicators: 15 minutes
- Testing: 15 minutes
- **Total: 1 hour**

### No Backend Changes Needed
- ✅ Memory is already configured
- ✅ Agent is already using memory
- ✅ No CDK changes required
- ✅ No deployment needed

## Testing Checklist

- [ ] Session persists across navigation
- [ ] Session persists across page refresh
- [ ] New Chat creates new session
- [ ] Different users get different sessions
- [ ] Sessions expire after 7 days
- [ ] Agent retrieves conversation history
- [ ] No repeated account ID requests

## Success Criteria

✅ Chat history visible after navigation
✅ Agent remembers previous conversation
✅ No repeated "What's your accountant ID?" questions
✅ Session ID persists in localStorage
✅ New Chat button creates fresh session
✅ Multi-user support works correctly

## Next Steps

1. Approve this plan
2. Implement session persistence
3. Test thoroughly
4. Deploy frontend
5. Verify memory working end-to-end

**Estimated completion: 1 hour**

Would you like me to proceed with implementation?
