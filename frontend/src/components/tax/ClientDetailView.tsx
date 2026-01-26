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
import { AddRequirementDialog } from './AddRequirementDialog';
import { 
  CheckCircle, 
  XCircle, 
  Mail, 
  AlertTriangle,
  AlertCircle,
  ArrowLeft,
  Phone,
  Calendar,
  RefreshCw,
  Plus
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
  const [showAddRequirementDialog, setShowAddRequirementDialog] = useState(false);
  const [operationMessage, setOperationMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    console.log('ClientDetailView mounted with clientId:', clientId);
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
      console.log('Client detail API response:', data);  // Debug
      console.log('Client detail response:', data);  // Debug
      
      if (data.clients && data.clients.length > 0) {
        // Find the specific client by ID (don't just take first one)
        const clientData = data.clients.find((c: any) => c.client_id === clientId) || data.clients[0];
        console.log('Selected client data:', clientData);
        setClient(clientData);
        
        // Transform required_documents to Document format
        const docs = clientData.required_documents?.map((doc: any) => ({
          type: doc.type,
          source: doc.source,
          received: doc.received,
          required: doc.required,
          received_date: doc.received_date,
          file_path: doc.file_path
        })) || [];
        console.log('Transformed documents:', docs);
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

  const handleDownloadDocument = async (documentType: string) => {
    setOperationMessage(null);
    try {
      // Load config
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      
      // Get ID token
      const idToken = auth.user?.id_token;
      
      if (!idToken) {
        setOperationMessage({type: 'error', text: 'Not authenticated'});
        return;
      }
      
      // Request download URL
      const response = await fetch(
        `${apiUrl}documents/${clientId}/${encodeURIComponent(documentType)}?tax_year=2026`,
        {
          headers: {
            'Authorization': `Bearer ${idToken}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get download URL');
      }
      
      const data = await response.json();
      
      // Open download URL in new tab
      window.open(data.download_url, '_blank');
      setOperationMessage({type: 'success', text: `Downloading ${documentType}...`});
      setTimeout(() => setOperationMessage(null), 2000);
      
    } catch (err) {
      console.error('Error downloading document:', err);
      setOperationMessage({type: 'error', text: err instanceof Error ? err.message : 'Failed to download document'});
    }
  };

  const handleSendReminder = async () => {
    if (!client) return;
    
    setOperationMessage(null);
    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      const idToken = auth.user?.id_token;

      const response = await fetch(`${apiUrl}batch-operations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          operation: 'send_reminders',
          client_ids: [clientId],
          options: {}
        })
      });

      const data = await response.json();
      
      if (data.success && data.succeeded > 0) {
        setOperationMessage({
          type: 'success', 
          text: `Reminder sent to ${client.client_name} with list of missing documents`
        });
        setTimeout(() => setOperationMessage(null), 3000);
      } else {
        const errorMsg = data.results?.[0]?.error || 'Failed to send reminder';
        setOperationMessage({type: 'error', text: errorMsg});
      }
    } catch (err) {
      setOperationMessage({
        type: 'error', 
        text: err instanceof Error ? err.message : 'Failed to send reminder'
      });
    }
  };

  const handleEscalate = async () => {
    // TODO: Implement escalate via batch operations or direct API
    setOperationMessage({type: 'success', text: 'Escalate functionality - coming soon'});
    setTimeout(() => setOperationMessage(null), 2000);
  };

  const handleAddRequirement = async (documentType: string, source: string) => {
    setOperationMessage(null);
    
    // Optimistic update - add to UI immediately
    const newDoc: Document = {
      type: documentType,
      source: source,
      received: false,
      required: true
    };
    setDocuments(prev => [...prev, newDoc]);
    
    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      const idToken = auth.user?.id_token;

      const response = await fetch(`${apiUrl}requirements`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_id: clientId,
          tax_year: 2026,
          operation: 'add',
          document_type: documentType,
          source: source,
          required: true
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setOperationMessage({type: 'success', text: `Added "${documentType}" to requirements`});
        setTimeout(() => setOperationMessage(null), 3000);
        // Don't fetch - keep optimistic update only
        // Data will refresh when user navigates away and back
        window.dispatchEvent(new Event('dashboard-refresh'));
      } else {
        // Revert optimistic update on error
        setDocuments(prev => prev.filter(d => d.type !== documentType));
        setOperationMessage({type: 'error', text: data.error || 'Failed to add requirement'});
      }
    } catch (err) {
      // Revert optimistic update on error
      setDocuments(prev => prev.filter(d => d.type !== documentType));
      setOperationMessage({type: 'error', text: err instanceof Error ? err.message : 'Failed to add requirement'});
    }
  };

  const handleRemoveRequirement = async (documentType: string) => {
    setOperationMessage(null);
    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      const idToken = auth.user?.id_token;

      const response = await fetch(`${apiUrl}requirements`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          client_id: clientId,
          tax_year: 2026,
          operation: 'remove',
          document_type: documentType
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setOperationMessage({type: 'success', text: `Removed "${documentType}" from requirements`});
        setTimeout(() => setOperationMessage(null), 3000);
        fetchClientDetails();
        // Trigger dashboard refresh
        window.dispatchEvent(new Event('dashboard-refresh'));
      } else {
        setOperationMessage({type: 'error', text: data.error || 'Failed to remove requirement'});
      }
    } catch (err) {
      setOperationMessage({type: 'error', text: err instanceof Error ? err.message : 'Failed to remove requirement'});
    }
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

  // Debug: Log documents state at render time
  console.log('Rendering with documents state:', documents.length, documents);

  return (
    <div className="space-y-6 p-6">
      {/* Operation Message */}
      {operationMessage && (
        <div className={`p-4 rounded-lg border ${
          operationMessage.type === 'success' 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2">
            {operationMessage.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600" />
            )}
            <span className={operationMessage.type === 'success' ? 'text-green-900' : 'text-red-900'}>
              {operationMessage.text}
            </span>
          </div>
        </div>
      )}

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
            size="sm"
            onClick={fetchClientDetails}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
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
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Documents</CardTitle>
              <CardDescription>Uploaded documents and requirements for 2026 tax return</CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddRequirementDialog(true)}
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Requirement
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No documents or requirements yet</p>
              <p className="text-sm mt-2">Click "Add Requirement" to specify what this client needs</p>
            </div>
          ) : (
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
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{doc.type}</span>
                        {doc.required && (
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                            Required
                          </span>
                        )}
                      </div>
                      {doc.received && doc.received_date && (
                        <div className="text-xs text-gray-500">
                          Uploaded: {new Date(doc.received_date).toLocaleDateString()}
                        </div>
                      )}
                      {!doc.received && doc.source && (
                        <div className="text-xs text-gray-500">
                          Source: {doc.source}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {doc.received ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDownloadDocument(doc.type)}
                      >
                        Download
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveRequirement(doc.type)}
                        className="text-red-600 hover:text-red-700"
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
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

      {/* Add Requirement Dialog */}
      <AddRequirementDialog
        open={showAddRequirementDialog}
        onClose={() => setShowAddRequirementDialog(false)}
        onAdd={handleAddRequirement}
        clientName={client?.client_name || ''}
      />
    </div>
  );
}
