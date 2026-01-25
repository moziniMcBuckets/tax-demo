"use client"

import React, { useState } from "react"
import ChatInterface from "@/components/chat/ChatInterface"
import { ClientDashboard } from "@/components/tax/ClientDashboard"
import { ClientDetailView } from "@/components/tax/ClientDetailView"
import { ClientUploadPortal } from "@/components/tax/ClientUploadPortal"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/useAuth"
import { GlobalContextProvider } from "@/app/context/GlobalContext"
import { MessageSquare, LayoutDashboard, Upload } from "lucide-react"

type View = 'chat' | 'dashboard' | 'upload';

export default function ChatPage() {
  const { isAuthenticated, signIn } = useAuth()
  const [currentView, setCurrentView] = useState<View>('chat')
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null)

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-4xl">Please sign in</p>
        <Button onClick={() => signIn()}>Sign In</Button>
      </div>
    )
  }

  const handleClientSelect = (clientId: string) => {
    setSelectedClientId(clientId)
    // Could navigate to detail view here
  }

  const handleRefresh = () => {
    // Refresh dashboard data
    window.location.reload()
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
            onClick={() => setCurrentView('dashboard')}
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
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto">
          {currentView === 'chat' && <ChatInterface />}
          {currentView === 'dashboard' && (
            <ClientDashboard 
              onClientSelect={handleClientSelect}
              onRefresh={handleRefresh}
            />
          )}
          {currentView === 'upload' && (
            <ClientUploadPortal
              clientId="test-client-id"
              uploadToken="test-token"
              apiUrl="https://api.example.com"
            />
          )}
        </div>
      </div>
    </GlobalContextProvider>
  )
}
