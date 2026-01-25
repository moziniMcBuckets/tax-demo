// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Type definitions for Tax Document Agent frontend components.
 */

export type ClientStatus = 'complete' | 'incomplete' | 'at_risk' | 'escalated';

export interface Client {
  client_id: string;
  client_name: string;
  email: string;
  phone?: string;
  status: ClientStatus;
  completion_percentage: number;
  total_required: number;
  total_received: number;
  missing_documents: string[];
  followup_count: number;
  last_followup?: number;
  last_followup_date?: string;
  next_followup_date?: string;
  days_until_escalation?: number;
  next_action: string;
}

export interface ClientSummary {
  total_clients: number;
  complete: number;
  incomplete: number;
  at_risk: number;
  escalated: number;
}

export interface StatusResponse {
  summary: ClientSummary;
  clients: Client[];
  generated_at: string;
}

export interface Document {
  type: string;
  source: string;
  received: boolean;
  last_checked: string;
}

export interface DocumentCheckResponse {
  client_id: string;
  tax_year: number;
  status: ClientStatus;
  completion_percentage: number;
  required_documents: Document[];
  received_documents: any[];
  missing_documents: { type: string; source: string; required: boolean }[];
  last_checked: string;
}
