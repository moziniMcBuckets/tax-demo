// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Client Dashboard Component
 * 
 * Displays a table view of all clients with their document collection status.
 * Features:
 * - Color-coded status indicators
 * - Sortable columns
 * - Filter by status
 * - Search by client name
 * - Click to view details
 */

import { useState, useEffect } from 'react';
import { Client, ClientSummary, ClientStatus } from '@/types/tax/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from 'react-oidc-context';
import { 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Search,
  RefreshCw
} from 'lucide-react';

interface ClientDashboardProps {
  onClientSelect: (clientId: string) => void;
  onRefresh: () => void;
}

export function ClientDashboard({ onClientSelect, onRefresh }: ClientDashboardProps) {
  const auth = useAuth();
  const [clients, setClients] = useState<Client[]>([]);
  const [summary, setSummary] = useState<ClientSummary | null>(null);
  const [filter, setFilter] = useState<ClientStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedClients, setSelectedClients] = useState<Set<string>>(new Set());
  const [bulkOperationInProgress, setBulkOperationInProgress] = useState(false);
  const [bulkOperationStatus, setBulkOperationStatus] = useState<string>('');

  // Fetch clients data
  useEffect(() => {
    if (auth.isAuthenticated && !loading) {
      fetchClients();
    }
  }, [auth.isAuthenticated]);

  // Refresh when dashboard becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && auth.isAuthenticated) {
        fetchClients();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Listen for refresh events
    const handleRefreshEvent = () => fetchClients();
    window.addEventListener('dashboard-refresh', handleRefreshEvent);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('dashboard-refresh', handleRefreshEvent);
    };
  }, [auth.isAuthenticated]);

  const fetchClients = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load config
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      
      // Get ID token from react-oidc-context
      const idToken = auth.user?.id_token;
      
      if (!idToken) {
        throw new Error('Not authenticated');
      }
      
      // Fetch ALL clients from API (explicitly no client_id parameter)
      const url = new URL(`${apiUrl}clients`);
      url.searchParams.set('accountant_id', 'acc_test_001');
      url.searchParams.set('filter', 'all');
      // Explicitly do NOT set client_id
      
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
      console.log('Fetched clients:', data);  // Debug log
      setClients(data.clients || []);
      setSummary(data.summary || null);
      
    } catch (err) {
      console.error('Error fetching clients:', err);
      setError(err instanceof Error ? err.message : 'Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  const toggleClientSelection = (clientId: string) => {
    setSelectedClients(prev => {
      const newSet = new Set(prev);
      if (newSet.has(clientId)) {
        newSet.delete(clientId);
      } else {
        newSet.add(clientId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedClients.size === filteredClients.length) {
      setSelectedClients(new Set());
    } else {
      setSelectedClients(new Set(filteredClients.map(c => c.client_id)));
    }
  };

  const handleBulkSendReminders = async () => {
    if (selectedClients.size === 0) {
      alert('Please select at least one client');
      return;
    }

    setBulkOperationInProgress(true);
    setBulkOperationStatus(`Sending reminders to ${selectedClients.size} clients...`);

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
          client_ids: Array.from(selectedClients),
          options: {}
        })
      });

      const data = await response.json();
      
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      setSelectedClients(new Set());
      
      alert(`Reminders sent!\nSuccess: ${data.succeeded}\nFailed: ${data.failed}`);
      fetchClients();  // Refresh data
      
    } catch (err) {
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      alert(`Error: ${err instanceof Error ? err.message : 'Failed to send reminders'}`);
    }
  };

  const handleBulkSendUploadLinks = async () => {
    if (selectedClients.size === 0) {
      alert('Please select at least one client');
      return;
    }

    setBulkOperationInProgress(true);
    setBulkOperationStatus(`Sending upload links to ${selectedClients.size} clients...`);

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
          operation: 'send_upload_links',
          client_ids: Array.from(selectedClients),
          options: { days_valid: 30 }
        })
      });

      const data = await response.json();
      
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      setSelectedClients(new Set());
      
      alert(`Upload links sent!\nSuccess: ${data.succeeded}\nFailed: ${data.failed}`);
      fetchClients();
      
    } catch (err) {
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      alert(`Error: ${err instanceof Error ? err.message : 'Failed to send upload links'}`);
    }
  };

  const handleBulkDownload = async () => {
    if (selectedClients.size === 0) {
      alert('Please select at least one client');
      return;
    }

    setBulkOperationInProgress(true);
    setBulkOperationStatus(`Creating ZIP archive for ${selectedClients.size} clients...`);

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
          operation: 'download_all',
          client_ids: Array.from(selectedClients),
          options: {}
        })
      });

      const data = await response.json();
      
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      
      if (data.success && data.download_url) {
        // Open download URL
        window.open(data.download_url, '_blank');
        alert(`ZIP created with ${data.total_files} files!\nDownload started.`);
      } else {
        alert(`Error: ${data.error || 'Failed to create ZIP'}`);
      }
      
      setSelectedClients(new Set());
      
    } catch (err) {
      setBulkOperationInProgress(false);
      setBulkOperationStatus('');
      alert(`Error: ${err instanceof Error ? err.message : 'Failed to download documents'}`);
    }
  };

  // Status badge styling
  const getStatusBadge = (status: ClientStatus) => {
    const styles = {
      complete: 'bg-green-100 text-green-800 border-green-300',
      incomplete: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      at_risk: 'bg-orange-100 text-orange-800 border-orange-300',
      escalated: 'bg-red-100 text-red-800 border-red-300',
    };

    const icons = {
      complete: <CheckCircle className="w-4 h-4" />,
      incomplete: <Clock className="w-4 h-4" />,
      at_risk: <AlertTriangle className="w-4 h-4" />,
      escalated: <AlertCircle className="w-4 h-4" />,
    };

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
        {icons[status]}
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  // Filter and search clients
  const filteredClients = clients.filter(client => {
    const matchesFilter = filter === 'all' || client.status === filter;
    const matchesSearch = client.client_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Summary cards
  const summaryCards = summary ? [
    { label: 'Total Clients', value: summary.total_clients, color: 'text-blue-600' },
    { label: 'Complete', value: summary.complete, color: 'text-green-600' },
    { label: 'Incomplete', value: summary.incomplete, color: 'text-yellow-600' },
    { label: 'At Risk', value: summary.at_risk, color: 'text-orange-600' },
    { label: 'Escalated', value: summary.escalated, color: 'text-red-600' },
  ] : [];

  return (
    <div className="space-y-6 p-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {summaryCards.map((card, index) => (
            <Card key={index}>
              <CardHeader className="pb-2">
                <CardDescription>{card.label}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${card.color}`}>
                  {card.value}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters and Search */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Client Status</CardTitle>
              <CardDescription>Track document collection progress</CardDescription>
            </div>
            <Button onClick={() => { 
              setSelectedClients(new Set()); // Clear selections
              fetchClients(); 
              onRefresh(); 
            }} variant="outline" size="sm" disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filter buttons */}
          <div className="flex flex-wrap gap-2 mb-4 items-center justify-between">
            <div className="flex gap-2">
              <Button
                variant={filter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                All
              </Button>
              <Button
                variant={filter === 'incomplete' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('incomplete')}
              >
                Incomplete
              </Button>
              <Button
                variant={filter === 'at_risk' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('at_risk')}
              >
                At Risk
              </Button>
              <Button
                variant={filter === 'escalated' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilter('escalated')}
              >
                Escalated
              </Button>
            </div>

            {/* Bulk Actions */}
            {selectedClients.size > 0 && (
              <div className="flex gap-2 items-center">
                <span className="text-sm text-gray-600">
                  {selectedClients.size} selected
                </span>
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleBulkSendReminders}
                  disabled={bulkOperationInProgress}
                >
                  Send Reminders
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleBulkSendUploadLinks}
                  disabled={bulkOperationInProgress}
                >
                  Send Upload Links
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBulkDownload}
                  disabled={bulkOperationInProgress}
                >
                  Download All
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedClients(new Set())}
                >
                  Clear
                </Button>
              </div>
            )}
          </div>

          {/* Bulk Operation Status */}
          {bulkOperationStatus && (
            <div className="mb-4 p-3 bg-blue-50 text-blue-800 rounded-md flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>{bulkOperationStatus}</span>
            </div>
          )}

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              placeholder="Search clients..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Client Table */}
          {loading && (
            <div className="text-center py-8">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400 mb-2" />
              <p className="text-gray-500">Loading clients...</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <AlertCircle className="w-8 h-8 mx-auto text-red-500 mb-2" />
              <p className="text-red-600">{error}</p>
              <Button onClick={fetchClients} variant="outline" size="sm" className="mt-4">
                Try Again
              </Button>
            </div>
          )}

          {!loading && !error && (
            <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedClients.size === filteredClients.length && filteredClients.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Client</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Missing</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reminders</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredClients.map((client) => (
                  <tr 
                    key={client.client_id}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedClients.has(client.client_id)}
                        onChange={() => toggleClientSelection(client.client_id)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded"
                      />
                    </td>
                    <td 
                      className="px-4 py-3 cursor-pointer"
                      onClick={() => onClientSelect(client.client_id)}
                    >
                      <div className="font-medium text-gray-900">{client.client_name}</div>
                      <div className="text-sm text-gray-500">{client.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      {getStatusBadge(client.status)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              client.completion_percentage === 100 ? 'bg-green-500' :
                              client.completion_percentage >= 50 ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${client.completion_percentage}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">
                          {client.completion_percentage}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">
                        {client.missing_documents.length} docs
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-900">
                        {client.followup_count}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-gray-600">
                        {client.next_action.substring(0, 40)}...
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          onClientSelect(client.client_id);
                        }}
                      >
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredClients.length === 0 && !loading && !error && (
              <div className="text-center py-8 text-gray-500">
                No clients found matching your criteria
              </div>
            )}
          </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
