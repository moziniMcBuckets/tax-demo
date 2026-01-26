"use client"

import React, { useState } from "react"
import ChatInterface from "@/components/chat/ChatInterface"
import { ClientDashboard } from "@/components/tax/ClientDashboard"
import { ClientDetailView } from "@/components/tax/ClientDetailView"
import { ClientUploadPortal } from "@/components/tax/ClientUploadPortal"
import { NewClientIntake } from "@/components/tax/NewClientIntake"
import { DebugPanel } from "@/components/tax/DebugPanel"
import { AuthForms } from "@/components/auth/AuthForms"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/useAuth"
import { GlobalContextProvider } from "@/app/context/GlobalContext"
import { MessageSquare, LayoutDashboard, Upload, UserPlus } from "lucide-react"

type View = 'chat' | 'dashboard' | 'upload' | 'newClient';

export default function ChatPage() {
  const { isAuthenticated, signIn } = useAuth()
  const [currentView, setCurrentView] = useState<View>('chat')
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null)
  const [showDetailView, setShowDetailView] = useState(false)
  const [dashboardKey, setDashboardKey] = useState(0)  // Force dashboard remount

  if (!isAuthenticated) {
    return <AuthForms />
  }

  const handleClientSelect = (clientId: string) => {
    setSelectedClientId(clientId)
    setShowDetailView(true)
  }

  const handleBackToDashboard = () => {
    setShowDetailView(false)
    setSelectedClientId(null)
    setDashboardKey(prev => prev + 1)  // Force dashboard to remount and fetch fresh data
  }

  const handleRefresh = () => {
    // Trigger dashboard refresh without page reload
    window.dispatchEvent(new Event('dashboard-refresh'))
  }

  return (
    <GlobalContextProvider>
      <div className="relative h-screen flex flex-col">
        {/* Navigation Tabs */}
        <div className="flex gap-2 p-4 border-b bg-white">
          <Button
            variant={currentView === 'chat' ? 'default' : 'outline'}
            onClick={() => setCurrentView('chat')}
            className="flex items-center gap-2"
          >
            <MessageSquare className="w-4 h-4" />
            Chat
          </Button>
          <Button
            variant={currentView === 'dashboard' ? 'default' : 'outline'}
            onClick={() => {
              setCurrentView('dashboard')
              setShowDetailView(false)
              setSelectedClientId(null)
              // Clear any URL parameters
              if (typeof window !== 'undefined') {
                window.history.replaceState({}, '', window.location.pathname)
              }
            }}
            className="flex items-center gap-2"
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </Button>
          <Button
            variant={currentView === 'upload' ? 'default' : 'outline'}
            onClick={() => setCurrentView('upload')}
            className="flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Upload Documents
          </Button>
          <Button
            variant={currentView === 'newClient' ? 'default' : 'outline'}
            onClick={() => setCurrentView('newClient')}
            className="flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" />
            New Client
          </Button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto">
          {currentView === 'chat' && <ChatInterface />}
          {currentView === 'dashboard' && !showDetailView && (
            <ClientDashboard 
              key={`dashboard-${dashboardKey}-${currentView}`}
              onClientSelect={handleClientSelect}
              onRefresh={handleRefresh}
            />
          )}
          {currentView === 'dashboard' && showDetailView && selectedClientId && (
            <div className="p-6">
              <Button onClick={handleBackToDashboard} variant="outline" className="mb-4">
                ← Back to Dashboard
              </Button>
              <ClientDetailView 
                key={`detail-${selectedClientId}`}
                clientId={selectedClientId}
                onBack={handleBackToDashboard}
              />
            </div>
          )}
          {currentView === 'upload' && (
            <ClientUploadPortal
              clientId="test-client-id"
              uploadToken="test-token"
              apiUrl="https://api.example.com"
            />
          )}
          {currentView === 'newClient' && (
            <NewClientIntake 
              onClientCreated={() => {
                setDashboardKey(prev => prev + 1);  // Force dashboard to fetch fresh data
                setCurrentView('dashboard');
              }}
            />
          )}
        </div>

        {/* Debug Panel */}
        <DebugPanel 
          selectedClientId={selectedClientId}
          showDetailView={showDetailView}
          currentView={currentView}
        />
      </div>
    </GlobalContextProvider>
  )
}
