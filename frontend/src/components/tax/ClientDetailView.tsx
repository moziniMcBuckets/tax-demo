// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Client Detail View Component
 * 
 * Shows detailed information for a single client including:
 * - Client information
 * - Document checklist
 * - Follow-up history
 * - Quick actions
 */

import { useState, useEffect } from 'react';
import { Client, Document } from '@/types/tax/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useAuth } from 'react-oidc-context';
import { 
  CheckCircle, 
  XCircle, 
  Mail, 
  AlertTriangle,
  AlertCircle,
  ArrowLeft,
  Phone,
  Calendar,
  RefreshCw
} from 'lucide-react';

interface ClientDetailViewProps {
  clientId: string;
  onBack: () => void;
}

export function ClientDetailView({ 
  clientId, 
  onBack
}: ClientDetailViewProps) {
  const auth = useAuth();
  const [client, setClient] = useState<Client | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (auth.isAuthenticated) {
      fetchClientDetails();
    }
  }, [clientId, auth.isAuthenticated]);

  const fetchClientDetails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load config
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      
      // Get ID token
      const idToken = auth.user?.id_token;
      
      if (!idToken) {
        throw new Error('Not authenticated');
      }
      
      // Fetch client details from API
      const response = await fetch(`${apiUrl}clients?accountant_id=acc_test_001&client_id=${clientId}`, {
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch client details: ${response.statusText}`);
      }
      
      const data = await response.json();
      if (data.clients && data.clients.length > 0) {
        const clientData = data.clients[0];
        setClient(clientData);
        
        // Transform required_documents to Document format
        const docs = clientData.required_documents?.map((doc: any) => ({
          type: doc.type,
          source: doc.source,
          received: doc.received
        })) || [];
        setDocuments(docs);
      } else {
        throw new Error('Client not found');
      }
      
    } catch (err) {
      console.error('Error fetching client details:', err);
      setError(err instanceof Error ? err.message : 'Failed to load client details');
    } finally {
      setLoading(false);
    }
  };

  const handleSendReminder = async () => {
    // TODO: Implement send reminder via API
    alert('Send reminder functionality - to be implemented');
  };

  const handleEscalate = async () => {
    // TODO: Implement escalate via API
    alert('Escalate functionality - to be implemented');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400 mb-2" />
          <p className="text-gray-500">Loading client details...</p>
        </div>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 mx-auto text-red-500 mb-2" />
          <p className="text-red-600">{error || 'Client not found'}</p>
          <Button onClick={onBack} variant="outline" className="mt-4">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{client.client_name}</h1>
            <p className="text-gray-500">{client.email}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={handleSendReminder}
            disabled={loading || client.status === 'complete'}
          >
            <Mail className="w-4 h-4 mr-2" />
            Send Reminder
          </Button>
          <Button 
            variant="destructive" 
            onClick={handleEscalate}
            disabled={loading || client.status === 'escalated'}
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Escalate
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Completion</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{client.completion_percentage}%</div>
            <div className="text-sm text-gray-500">
              {client.total_received} of {client.total_required} documents
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Reminders Sent</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{client.followup_count}</div>
            <div className="text-sm text-gray-500">
              {client.last_followup_date ? 
                `Last: ${new Date(client.last_followup_date).toLocaleDateString()}` : 
                'None sent'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Missing Documents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-orange-600">
              {client.missing_documents.length}
            </div>
            <div className="text-sm text-gray-500">
              {client.missing_documents.length === 0 ? 'All received' : 'Need attention'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Days to Escalation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">
              {client.days_until_escalation ?? 'N/A'}
            </div>
            <div className="text-sm text-gray-500">
              {client.status === 'escalated' ? 'Already escalated' : 'Until escalation'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Document Checklist */}
      <Card>
        <CardHeader>
          <CardTitle>Document Checklist</CardTitle>
          <CardDescription>Required documents for 2024 tax return</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {documents.map((doc, index) => (
              <div 
                key={index}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  {doc.received ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <div className="font-medium">{doc.type}</div>
                    <div className="text-sm text-gray-500">{doc.source}</div>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  {doc.received ? 'Received' : 'Missing'}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Contact Information */}
      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-gray-400" />
              <span>{client.email}</span>
            </div>
            {client.phone && (
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-gray-400" />
                <span>{client.phone}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Next Action */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Next Action</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg">
            <Calendar className="w-5 h-5 text-blue-600 mt-0.5" />
            <div>
              <div className="font-medium text-blue-900">{client.next_action}</div>
              {client.next_followup_date && (
                <div className="text-sm text-blue-700 mt-1">
                  Scheduled for: {new Date(client.next_followup_date).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
