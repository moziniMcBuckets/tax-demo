// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Send Upload Link Form Component
 * 
 * Allows accountants to:
 * - Select a client from dropdown
 * - Configure reminder timing preferences
 * - Add custom message
 * - Send secure upload link via email
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from 'react-oidc-context';
import { 
  Send, 
  CheckCircle, 
  AlertCircle, 
  RefreshCw,
  Mail,
  Clock,
  Settings
} from 'lucide-react';

interface Client {
  client_id: string;
  client_name: string;
  email: string;
  phone?: string;
  sms_enabled?: boolean;
  status: string;
}

interface ReminderPreferences {
  first_reminder_days: number;
  second_reminder_days: number;
  third_reminder_days: number;
  escalation_days: number;
}

const DEFAULT_PREFERENCES: ReminderPreferences = {
  first_reminder_days: 7,
  second_reminder_days: 14,
  third_reminder_days: 21,
  escalation_days: 30
};

export function SendUploadLinkForm() {
  const auth = useAuth();
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string>('');
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [daysValid, setDaysValid] = useState<number>(30);
  const [customMessage, setCustomMessage] = useState<string>('');
  const [sendVia, setSendVia] = useState<string>('both');  // 'email', 'sms', or 'both'
  const [reminderPreferences, setReminderPreferences] = useState<ReminderPreferences>(DEFAULT_PREFERENCES);
  const [useCustomReminders, setUseCustomReminders] = useState<boolean>(false);
  
  const [loading, setLoading] = useState(false);
  const [loadingClients, setLoadingClients] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Fetch clients on mount
  useEffect(() => {
    if (auth.isAuthenticated) {
      fetchClients();
    }
  }, [auth.isAuthenticated]);

  // Update selected client when selection changes
  useEffect(() => {
    const client = clients.find(c => c.client_id === selectedClientId);
    setSelectedClient(client || null);
  }, [selectedClientId, clients]);

  const fetchClients = async () => {
    setLoadingClients(true);
    setError(null);
    
    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      const idToken = auth.user?.id_token;
      
      if (!idToken) {
        throw new Error('Not authenticated');
      }
      
      const url = new URL(`${apiUrl}clients`);
      url.searchParams.set('filter', 'all');
      
      const response = await fetch(url.toString(), {
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch clients: ${response.statusText}`);
      }
      
      const data = await response.json();
      setClients(data.clients || []);
      
    } catch (err) {
      console.error('Error fetching clients:', err);
      setError(err instanceof Error ? err.message : 'Failed to load clients');
    } finally {
      setLoadingClients(false);
    }
  };

  const handleSendUploadLink = async () => {
    if (!selectedClientId) {
      setError('Please select a client');
      return;
    }

    if (daysValid < 1 || daysValid > 90) {
      setError('Days valid must be between 1 and 90');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      const idToken = auth.user?.id_token;

      if (!idToken) {
        throw new Error('Not authenticated');
      }

      // Send upload link via batch operations API
      const response = await fetch(`${apiUrl}batch-operations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          operation: 'send_upload_links',
          client_ids: [selectedClientId],
          options: {
            days_valid: daysValid,
            send_via: sendVia,
            custom_message: customMessage || undefined,
            reminder_preferences: useCustomReminders ? reminderPreferences : undefined
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to send upload link');
      }

      const data = await response.json();
      
      if (data.results && data.results[0]) {
        const clientResult = data.results[0];
        if (clientResult.success) {
          setSuccess(true);
          setResult(clientResult);
          
          // Reset form
          setSelectedClientId('');
          setCustomMessage('');
          setUseCustomReminders(false);
          setReminderPreferences(DEFAULT_PREFERENCES);
          
          // Clear success message after 5 seconds
          setTimeout(() => {
            setSuccess(false);
            setResult(null);
          }, 5000);
        } else {
          throw new Error(clientResult.error || 'Failed to send upload link');
        }
      } else {
        throw new Error('Unexpected response format');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send upload link');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Send Upload Link</h1>
        <p className="text-gray-600 mt-2">
          Send a secure document upload link to a client via email
        </p>
      </div>

      {/* Main Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Upload Link Configuration
          </CardTitle>
          <CardDescription>
            Select a client and configure the upload link settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Client Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Select Client *
            </label>
            <div className="flex gap-2">
              <select
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="flex-1 p-2 border rounded-md"
                disabled={loading || loadingClients}
              >
                <option value="">
                  {loadingClients ? 'Loading clients...' : 'Choose a client...'}
                </option>
                {clients.map(client => (
                  <option key={client.client_id} value={client.client_id}>
                    {client.client_name} ({client.email})
                  </option>
                ))}
              </select>
              <Button
                onClick={fetchClients}
                variant="outline"
                size="sm"
                disabled={loadingClients}
              >
                <RefreshCw className={`w-4 h-4 ${loadingClients ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            {selectedClient && (
              <p className="text-sm text-gray-500 mt-2">
                Status: <span className="font-medium">{selectedClient.status}</span>
                {selectedClient.phone && (
                  <span className="ml-4">
                    📱 Phone: {selectedClient.phone}
                    {selectedClient.sms_enabled && <span className="text-green-600 ml-2">✓ SMS enabled</span>}
                    {!selectedClient.sms_enabled && <span className="text-gray-400 ml-2">SMS disabled</span>}
                  </span>
                )}
              </p>
            )}
          </div>

          {/* Link Validity */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Link Valid For (days) *
            </label>
            <Input
              type="number"
              min="1"
              max="90"
              value={daysValid}
              onChange={(e) => setDaysValid(parseInt(e.target.value) || 30)}
              disabled={loading}
              className="max-w-xs"
            />
            <p className="text-sm text-gray-500 mt-1">
              The upload link will expire after this many days (1-90)
            </p>
          </div>

          {/* Channel Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Send Via *
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="sendVia"
                  value="email"
                  checked={sendVia === 'email'}
                  onChange={(e) => setSendVia(e.target.value)}
                  disabled={loading}
                  className="rounded"
                />
                <span className="text-sm">Email only</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="sendVia"
                  value="sms"
                  checked={sendVia === 'sms'}
                  onChange={(e) => setSendVia(e.target.value)}
                  disabled={loading || !selectedClient?.phone || !selectedClient?.sms_enabled}
                  className="rounded"
                />
                <span className="text-sm">SMS only</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="sendVia"
                  value="both"
                  checked={sendVia === 'both'}
                  onChange={(e) => setSendVia(e.target.value)}
                  disabled={loading}
                  className="rounded"
                />
                <span className="text-sm">Both (Email + SMS)</span>
              </label>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              {sendVia === 'email' && 'Email only ($0.0001 per send)'}
              {sendVia === 'sms' && selectedClient?.phone && selectedClient?.sms_enabled && 'SMS only ($0.00645 per send)'}
              {sendVia === 'sms' && (!selectedClient?.phone || !selectedClient?.sms_enabled) && 'SMS not available (no phone or SMS disabled)'}
              {sendVia === 'both' && selectedClient?.phone && selectedClient?.sms_enabled && 'Email + SMS ($0.00655 per send)'}
              {sendVia === 'both' && (!selectedClient?.phone || !selectedClient?.sms_enabled) && 'Email only (SMS not available)'}
            </p>
          </div>

          {/* Custom Message */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Custom Message (optional)
            </label>
            <Textarea
              value={customMessage}
              onChange={(e) => setCustomMessage(e.target.value)}
              placeholder="Add a personalized message to include in the email..."
              disabled={loading}
              rows={4}
            />
            <p className="text-sm text-gray-500 mt-1">
              This message will be included in the email sent to the client
            </p>
          </div>

          {/* Reminder Preferences */}
          <div className="border-t pt-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-gray-600" />
                <h3 className="text-lg font-medium">Reminder Schedule</h3>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useCustomReminders}
                  onChange={(e) => setUseCustomReminders(e.target.checked)}
                  disabled={loading}
                  className="rounded"
                />
                <span className="text-sm">Customize for this client</span>
              </label>
            </div>

            {!useCustomReminders && (
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Default reminder schedule:</strong>
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• First reminder: {DEFAULT_PREFERENCES.first_reminder_days} days after upload link sent</li>
                  <li>• Second reminder: {DEFAULT_PREFERENCES.second_reminder_days} days after upload link sent</li>
                  <li>• Third reminder: {DEFAULT_PREFERENCES.third_reminder_days} days after upload link sent</li>
                  <li>• Escalation: {DEFAULT_PREFERENCES.escalation_days} days after upload link sent</li>
                </ul>
              </div>
            )}

            {useCustomReminders && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    First Reminder (days)
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="90"
                    value={reminderPreferences.first_reminder_days}
                    onChange={(e) => setReminderPreferences({
                      ...reminderPreferences,
                      first_reminder_days: parseInt(e.target.value) || 7
                    })}
                    disabled={loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Second Reminder (days)
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="90"
                    value={reminderPreferences.second_reminder_days}
                    onChange={(e) => setReminderPreferences({
                      ...reminderPreferences,
                      second_reminder_days: parseInt(e.target.value) || 14
                    })}
                    disabled={loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Third Reminder (days)
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="90"
                    value={reminderPreferences.third_reminder_days}
                    onChange={(e) => setReminderPreferences({
                      ...reminderPreferences,
                      third_reminder_days: parseInt(e.target.value) || 21
                    })}
                    disabled={loading}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Escalation (days)
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="90"
                    value={reminderPreferences.escalation_days}
                    onChange={(e) => setReminderPreferences({
                      ...reminderPreferences,
                      escalation_days: parseInt(e.target.value) || 30
                    })}
                    disabled={loading}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Send Button */}
          <Button
            onClick={handleSendUploadLink}
            disabled={!selectedClientId || loading}
            className="w-full"
            size="lg"
          >
            <Send className="w-4 h-4 mr-2" />
            {loading ? 'Sending...' : 'Send Upload Link'}
          </Button>

          {/* Success Message */}
          {success && result && (
            <div className="flex items-start gap-3 p-4 bg-green-50 text-green-800 rounded-md border border-green-200">
              <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium">Upload link sent successfully!</p>
                <p className="text-sm mt-1">{result.message}</p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 text-red-800 rounded-md border border-red-200">
              <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium">Error</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>How It Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-gray-600">
          <p>1. Select the client you want to send an upload link to</p>
          <p>2. Configure how long the link should remain valid (1-90 days)</p>
          <p>3. Optionally add a personalized message</p>
          <p>4. Optionally customize the reminder schedule for this client</p>
          <p>5. Click "Send Upload Link" to email the secure link to the client</p>
          <p className="mt-4 text-xs text-gray-500">
            The client will receive an email with a secure, unique link to upload their tax documents.
            No login is required - the link contains a secure token that grants access.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
