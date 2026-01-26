// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Client Upload Page
 * 
 * Public page for clients to upload tax documents using a secure token.
 * No authentication required - access is granted via URL token.
 */

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ClientUploadPortal } from '@/components/tax/ClientUploadPortal';
import LoadingSpinner from '@/components/loaders/LoadingSpinner';

function UploadPageContent() {
  const searchParams = useSearchParams();
  const [clientId, setClientId] = useState<string | null>(null);
  const [uploadToken, setUploadToken] = useState<string | null>(null);
  const [apiUrl, setApiUrl] = useState<string>('');

  useEffect(() => {
    setClientId(searchParams.get('client'));
    setUploadToken(searchParams.get('token'));
    
    // Load API URL from aws-exports.json
    fetch('/aws-exports.json')
      .then(res => res.json())
      .then(config => {
        setApiUrl(config.feedbackApiUrl || 'https://api.example.com');
      })
      .catch(err => {
        console.error('Failed to load config:', err);
        setApiUrl('https://api.example.com');
      });
  }, [searchParams]);

  if (clientId === null || uploadToken === null || !apiUrl) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <LoadingSpinner message="Loading upload portal..." />
      </div>
    );
  }

  if (!clientId || !uploadToken) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Invalid Upload Link</h1>
          <p className="text-gray-600 mb-4">
            This upload link is invalid or incomplete. Please check the link in your email and try again.
          </p>
          <p className="text-sm text-gray-500">
            If you continue to have issues, please contact your accountant.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ClientUploadPortal
      clientId={clientId}
      uploadToken={uploadToken}
      apiUrl={apiUrl}
    />
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading upload portal..." />}>
      <UploadPageContent />
    </Suspense>
  );
}
