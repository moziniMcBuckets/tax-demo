// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Client Upload Portal Component
 * 
 * Allows clients to securely upload tax documents using S3 presigned URLs.
 * Clients access this via a secure link sent by their accountant.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Upload, CheckCircle, AlertCircle, FileText } from 'lucide-react';

const DOCUMENT_TYPES = [
  'W-2',
  '1099-INT',
  '1099-DIV',
  '1099-MISC',
  '1099-NEC',
  '1099-B',
  '1099-R',
  'Prior Year Tax Return',
  'Receipts',
  'Other',
];

interface ClientUploadPortalProps {
  clientId: string;
  uploadToken: string;
  apiUrl: string;
}

export function ClientUploadPortal({ clientId, uploadToken, apiUrl }: ClientUploadPortalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      // Validate file type
      if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
        setError('Only PDF files are allowed');
        return;
      }
      
      // Validate file size (10 MB max)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10 MB');
        return;
      }
      
      setFile(selectedFile);
      setSuccess(false);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !documentType) {
      setError('Please select a file and document type');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      // Step 1: Get presigned URL from API
      setUploadProgress(10);
      
      const urlResponse = await fetch(`${apiUrl}/upload-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          upload_token: uploadToken,
          filename: file.name,
          tax_year: 2024,
          document_type: documentType,
        }),
      });

      if (!urlResponse.ok) {
        const errorData = await urlResponse.json();
        throw new Error(errorData.error || 'Failed to get upload URL');
      }

      const { upload_url } = await urlResponse.json();
      setUploadProgress(30);

      // Step 2: Upload directly to S3 using presigned URL
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': 'application/pdf',
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Upload to S3 failed');
      }

      setUploadProgress(100);
      setSuccess(true);
      setUploadedFiles(prev => [...prev, `${documentType} - ${file.name}`]);
      
      // Reset form
      setFile(null);
      setDocumentType('');
      
      // Reset success message after 5 seconds
      setTimeout(() => setSuccess(false), 5000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Upload Tax Documents</h1>
          <p className="text-gray-600 mt-2">
            Securely upload your tax documents for 2024
          </p>
        </div>

        {/* Upload Form */}
        <Card>
          <CardHeader>
            <CardTitle>Document Upload</CardTitle>
            <CardDescription>
              Select the document type and upload your PDF file
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Document Type Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Document Type *
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="w-full p-2 border rounded-md"
                disabled={uploading}
              >
                <option value="">Select document type...</option>
                {DOCUMENT_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            {/* File Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Select File (PDF only, max 10 MB) *
              </label>
              <Input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                disabled={uploading}
              />
              {file && (
                <p className="text-sm text-gray-500 mt-2">
                  📄 {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
            </div>

            {/* Upload Progress */}
            {uploading && (
              <div className="space-y-2">
                <Progress value={uploadProgress} />
                <p className="text-sm text-gray-600 text-center">
                  Uploading... {uploadProgress}%
                </p>
              </div>
            )}

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={!file || !documentType || uploading}
              className="w-full"
            >
              <Upload className="w-4 h-4 mr-2" />
              {uploading ? 'Uploading...' : 'Upload Document'}
            </Button>

            {/* Success Message */}
            {success && (
              <div className="flex items-center gap-2 p-3 bg-green-50 text-green-800 rounded-md">
                <CheckCircle className="w-5 h-5" />
                <span>Document uploaded successfully! Your accountant will be notified.</span>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 text-red-800 rounded-md">
                <AlertCircle className="w-5 h-5" />
                <span>{error}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Uploaded Files List */}
        {uploadedFiles.length > 0 && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Uploaded Documents</CardTitle>
              <CardDescription>
                Documents you've uploaded in this session
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="flex items-center gap-2 p-2 bg-green-50 rounded">
                    <FileText className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-green-800">{file}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Instructions */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Upload Instructions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-gray-600">
            <p>1. Select the type of document you're uploading</p>
            <p>2. Choose your PDF file (must be under 10 MB)</p>
            <p>3. Click "Upload Document"</p>
            <p>4. Wait for confirmation</p>
            <p>5. Repeat for each document</p>
            <p className="mt-4 text-xs text-gray-500">
              Your documents are encrypted and securely stored. Only your accountant can access them.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
