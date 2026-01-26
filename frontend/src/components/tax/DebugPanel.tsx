// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

"use client"

/**
 * Debug Panel Component
 * 
 * Shows real-time debugging information for troubleshooting UI issues.
 * Press Ctrl+D to toggle visibility.
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface DebugPanelProps {
  selectedClientId: string | null;
  showDetailView: boolean;
  currentView: string;
}

export function DebugPanel({ selectedClientId, showDetailView, currentView }: DebugPanelProps) {
  const [visible, setVisible] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        setVisible(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  useEffect(() => {
    addLog(`View changed: ${currentView}, Detail: ${showDetailView}, Client: ${selectedClientId}`);
  }, [currentView, showDetailView, selectedClientId]);

  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev].slice(0, 20));
  };

  if (!visible) {
    return (
      <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-3 py-1 rounded text-xs">
        Press Ctrl+D for debug panel
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-96 overflow-auto z-50">
      <Card className="bg-gray-900 text-white border-gray-700">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Debug Panel</CardTitle>
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={() => setVisible(false)}
              className="text-white hover:bg-gray-800"
            >
              ✕
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <div className="space-y-1 p-2 bg-gray-800 rounded">
            <div><strong>Current View:</strong> {currentView}</div>
            <div><strong>Show Detail:</strong> {showDetailView ? 'Yes' : 'No'}</div>
            <div><strong>Selected Client ID:</strong> {selectedClientId || 'None'}</div>
            <div><strong>URL:</strong> {typeof window !== 'undefined' ? window.location.href : 'N/A'}</div>
          </div>

          <div className="space-y-1">
            <div className="font-bold">Event Log:</div>
            <div className="bg-gray-800 rounded p-2 max-h-48 overflow-auto">
              {logs.length === 0 ? (
                <div className="text-gray-400">No events yet</div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="text-xs font-mono">{log}</div>
                ))
              )}
            </div>
          </div>

          <Button 
            size="sm" 
            variant="outline" 
            onClick={() => setLogs([])}
            className="w-full"
          >
            Clear Logs
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
