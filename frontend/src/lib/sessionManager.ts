// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Session Manager
 * 
 * Manages chat session persistence across navigation and page refreshes.
 * Uses localStorage to store session ID per user, ensuring conversation
 * history is maintained and the agent remembers the accountant's identity.
 */

const SESSION_STORAGE_KEY = 'tax-agent-session-id';
const SESSION_EXPIRY_DAYS = 7; // Sessions expire after 7 days

interface SessionData {
  sessionId: string;
  userId: string;
  createdAt: string;
  lastAccessedAt: string;
}

/**
 * Get existing session or create new one for the user.
 * 
 * @param userId - User identifier from authentication
 * @returns Session ID string
 */
export function getOrCreateSession(userId: string): string {
  if (!userId) {
    console.warn('No userId provided, generating temporary session');
    return crypto.randomUUID();
  }

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
          
          console.log(`Restored session: ${data.sessionId} (age: ${Math.floor(daysSinceCreation)} days)`);
          return data.sessionId;
        } else {
          console.log('Session expired (>7 days), creating new one');
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

/**
 * Clear the current session from storage.
 */
export function clearSession(): void {
  localStorage.removeItem(SESSION_STORAGE_KEY);
  console.log('Session cleared');
}

/**
 * Start a new session for the user (clears old one).
 * 
 * @param userId - User identifier from authentication
 * @returns New session ID
 */
export function startNewSession(userId: string): string {
  clearSession();
  return getOrCreateSession(userId);
}

/**
 * Get current session data if it exists.
 * 
 * @returns SessionData or null if no session exists
 */
export function getCurrentSession(): SessionData | null {
  const stored = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!stored) return null;
  
  try {
    return JSON.parse(stored);
  } catch (e) {
    console.error('Error parsing session data:', e);
    return null;
  }
}

/**
 * Get session age in days.
 * 
 * @returns Number of days since session was created, or null if no session
 */
export function getSessionAge(): number | null {
  const session = getCurrentSession();
  if (!session) return null;
  
  const createdAt = new Date(session.createdAt);
  const now = new Date();
  const days = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60 * 24);
  
  return Math.floor(days);
}
