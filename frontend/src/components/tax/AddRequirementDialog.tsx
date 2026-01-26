// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Add Requirement Dialog Component
 * 
 * Modal dialog for adding document requirements to a client.
 */

import { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const COMMON_DOCUMENTS = [
  'W-2',
  '1099-INT',
  '1099-DIV',
  '1099-MISC',
  '1099-NEC',
  '1099-B',
  '1099-R',
  'Schedule C (Business)',
  'Schedule E (Rental)',
  'Schedule K-1',
  'Prior Year Tax Return',
  'Property Tax Statement',
  'Mortgage Interest (1098)',
  'Student Loan Interest (1098-E)',
  'Health Insurance (1095)',
  'Charitable Donations',
  'Business Expenses',
  'Custom...'
];

interface AddRequirementDialogProps {
  open: boolean;
  onClose: () => void;
  onAdd: (documentType: string, source: string) => void;
  clientName: string;
}

export function AddRequirementDialog({ open, onClose, onAdd, clientName }: AddRequirementDialogProps) {
  const [selectedType, setSelectedType] = useState('');
  const [customType, setCustomType] = useState('');
  const [source, setSource] = useState('');

  const handleAdd = () => {
    const docType = selectedType === 'Custom...' ? customType : selectedType;
    
    if (!docType) {
      alert('Please select or enter a document type');
      return;
    }

    onAdd(docType, source || 'To be determined');
    
    // Reset form
    setSelectedType('');
    setCustomType('');
    setSource('');
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Document Requirement</DialogTitle>
          <DialogDescription>
            Add a required document for {clientName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Document Type Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Document Type *</label>
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger>
                <SelectValue placeholder="Select document type..." />
              </SelectTrigger>
              <SelectContent>
                {COMMON_DOCUMENTS.map(doc => (
                  <SelectItem key={doc} value={doc}>{doc}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Custom Document Type */}
          {selectedType === 'Custom...' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Custom Document Type *</label>
              <Input
                placeholder="Enter document type..."
                value={customType}
                onChange={(e) => setCustomType(e.target.value)}
              />
            </div>
          )}

          {/* Source */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Source (Optional)</label>
            <Input
              placeholder="e.g., ABC Company, Chase Bank, IRS"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
            <p className="text-xs text-gray-500">
              Where the client should obtain this document
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleAdd}>
            Add Requirement
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
