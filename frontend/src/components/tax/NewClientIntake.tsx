// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * New Client Intake Form
 * 
 * Form for accountants to onboard new clients with their information
 * and initial document requirements.
 */

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAuth } from 'react-oidc-context';
import { UserPlus, Mail, Phone, Building, FileText, CheckCircle, AlertCircle } from 'lucide-react';

const CLIENT_TYPES = [
  { value: 'individual', label: 'Individual (W-2 Employee)' },
  { value: 'self_employed', label: 'Self-Employed / Freelancer' },
  { value: 'business', label: 'Business Owner' },
  { value: 'rental', label: 'Rental Property Owner' },
  { value: 'investor', label: 'Investor' },
];

interface NewClientIntakeProps {
  onClientCreated: () => void;
}

export function NewClientIntake({ onClientCreated }: NewClientIntakeProps) {
  const auth = useAuth();
  const [formData, setFormData] = useState({
    client_name: '',
    email: '',
    phone: '',
    sms_enabled: false,
    client_type: 'individual',
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.client_name || !formData.email) {
      setErrorMessage('Please fill in required fields: Name and Email');
      return;
    }

    setSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const configResponse = await fetch('/aws-exports.json');
      const config = await configResponse.json();
      const apiUrl = config.feedbackApiUrl;
      
      const idToken = auth.user?.id_token;
      
      if (!idToken) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${apiUrl}clients`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();
      
      if (data.success) {
        setSuccessMessage(`Client "${formData.client_name}" created successfully!`);
        
        // Reset form and switch to dashboard after showing success
        setTimeout(() => {
          setFormData({
            client_name: '',
            email: '',
            phone: '',
            sms_enabled: false,
            client_type: 'individual',
            notes: ''
          });
          onClientCreated();  // Switch to dashboard with refresh
        }, 1500);  // Show success for 1.5 seconds
      } else {
        setErrorMessage(data.error || 'Failed to create client');
      }
      
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to create client');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <UserPlus className="w-6 h-6 text-blue-600" />
            <div>
              <CardTitle>New Client Intake</CardTitle>
              <CardDescription>
                Add a new client to start tracking their tax documents
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Success Message */}
          {successMessage && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-green-900">{successMessage}</h4>
                  <p className="text-sm text-green-700 mt-1">
                    Next steps: Add document requirements and send upload link
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-900">Error</h4>
                  <p className="text-sm text-red-700">{errorMessage}</p>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Client Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Client Name *
              </label>
              <Input
                placeholder="John Smith"
                value={formData.client_name}
                onChange={(e) => setFormData({...formData, client_name: e.target.value})}
                required
              />
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Email Address *
              </label>
              <Input
                type="email"
                placeholder="john.smith@example.com"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
              <p className="text-xs text-gray-500">
                Used for sending reminders and upload links
              </p>
            </div>

            {/* Phone */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Phone className="w-4 h-4" />
                Phone Number (Optional)
              </label>
              <Input
                type="tel"
                placeholder="+12065551234"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
              />
              <p className="text-xs text-gray-500">
                E.164 format for SMS: +1XXXXXXXXXX (US only)
              </p>
            </div>

            {/* SMS Opt-in */}
            {formData.phone && (
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.sms_enabled}
                    onChange={(e) => setFormData({...formData, sms_enabled: e.target.checked})}
                    className="rounded"
                  />
                  <span className="text-sm font-medium">Enable SMS notifications</span>
                </label>
                <p className="text-xs text-gray-500 ml-6">
                  Client will receive text messages for reminders and updates ($0.00645 per SMS)
                </p>
              </div>
            )}

            {/* Client Type */}
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center gap-2">
                <Building className="w-4 h-4" />
                Client Type
              </label>
              <Select 
                value={formData.client_type} 
                onValueChange={(value) => setFormData({...formData, client_type: value})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CLIENT_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                Helps determine typical document requirements
              </p>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Notes (Optional)</label>
              <textarea
                className="w-full min-h-[100px] px-3 py-2 border rounded-md"
                placeholder="Any special considerations or notes about this client..."
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
              />
            </div>

            {/* Submit Button */}
            <div className="flex gap-3">
              <Button 
                type="submit" 
                className="flex-1"
                disabled={submitting}
              >
                {submitting ? 'Creating Client...' : 'Create Client'}
              </Button>
            </div>
          </form>

          {/* Info Box */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">After Creating Client:</h4>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Add document requirements specific to this client</li>
              <li>Send them a secure upload link</li>
              <li>Track their progress in the dashboard</li>
              <li>Send automated reminders as needed</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
