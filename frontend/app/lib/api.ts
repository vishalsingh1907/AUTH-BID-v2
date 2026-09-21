/**
 * SIH26100 — AuthBid API Client
 * Type-safe interface to the FastAPI backend with role-based authentication headers.
 */

import type {
  Tender,
  TenderChecklistItem,
  BidderSummary,
  BidderDetail,
  VerificationResult,
  VerificationResultsResponse,
  AuditTrailResponse,
  AnchorResponse,
  AnchorReceipt,
  OfficerDecision,
  ScrutinyReport,
  CopilotResponse,
  ShowCauseNotice,
  DocumentVaultItem,
  GraphData,
  ApiResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let currentActiveRole = "officer";

export function setActiveRole(role: string): void {
  currentActiveRole = role;
}

export function getActiveRole(): string {
  return currentActiveRole;
}

export async function fetchAPI<T>(endpoint: string, options?: RequestInit, role?: string): Promise<ApiResponse<T>> {
  const effectiveRole = role || currentActiveRole;
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-User-Role": effectiveRole,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = `${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // ── Tenders ──
  getTenders: async (): Promise<Tender[]> => {
    const res = await fetchAPI<Tender[]>("/api/tenders");
    return res.data || [];
  },

  getTender: async (id: string): Promise<Tender | null> => {
    const res = await fetchAPI<Tender>(`/api/tenders/${id}`);
    return res.data || null;
  },

  getChecklist: async (id: string): Promise<TenderChecklistItem[]> => {
    const res = await fetchAPI<{ checklist: TenderChecklistItem[] }>(`/api/tenders/${id}/checklist`);
    return res.data?.checklist || [];
  },

  // ── Bidders ──
  getBidders: async (): Promise<BidderSummary[]> => {
    const res = await fetchAPI<BidderSummary[]>("/api/bidders");
    return res.data || [];
  },

  getBidder: async (id: string): Promise<BidderDetail | null> => {
    const res = await fetchAPI<BidderDetail>(`/api/bidders/${id}`);
    return res.data || null;
  },

  getBidderVerification: async (bidderId: string, tenderId: string): Promise<VerificationResult | null> => {
    const res = await fetchAPI<VerificationResult>(
      `/api/bidders/${encodeURIComponent(bidderId)}/verification/${encodeURIComponent(tenderId)}`
    );
    return res.data || null;
  },

  // ── Verification Pipeline & Results ──
  runVerification: async (tenderId: string): Promise<VerificationResultsResponse> => {
    const res = await fetchAPI<VerificationResultsResponse>(`/api/verification/run/${encodeURIComponent(tenderId)}`, { method: "POST" });
    if (!res.data) throw new Error("Failed to run verification");
    return res.data;
  },

  getResults: async (tenderId: string): Promise<VerificationResultsResponse> => {
    const res = await fetchAPI<VerificationResultsResponse>(`/api/verification/results/${encodeURIComponent(tenderId)}`);
    if (!res.data) {
      return {
        tender_id: tenderId,
        total_bidders: 0,
        results: [],
        summary: { low_risk: 0, medium_risk: 0, high_risk: 0, critical_risk: 0 },
      };
    }
    return res.data;
  },

  // ── Audit Trail & Integrity ──
  getAuditTrail: async (): Promise<AuditTrailResponse> => {
    const res = await fetchAPI<AuditTrailResponse>("/api/verification/audit-trail");
    return res.data || { entries: [], total_entries: 0, chain_integrity: { valid: true } };
  },

  tamperAuditTrail: async (stepId?: string, role = "admin") => {
    return fetchAPI<{ tamper_result: any; chain_integrity: any }>(
      "/api/verification/tamper",
      {
        method: "POST",
        body: JSON.stringify({ step_id: stepId }),
      },
      role
    );
  },

  restoreAuditTrail: async (role = "admin") => {
    return fetchAPI<{ restore_result: any; chain_integrity: any }>("/api/verification/restore", { method: "POST" }, role);
  },

  anchorAuditTrail: async (role = "officer"): Promise<AnchorReceipt> => {
    const res = await fetchAPI<AnchorReceipt>("/api/verification/anchor", { method: "POST" }, role);
    if (!res.data) throw new Error("Failed to anchor audit trail");
    return res.data;
  },

  getAnchorReceipt: async (): Promise<AnchorResponse> => {
    const res = await fetchAPI<AnchorResponse>("/api/verification/anchor");
    return res.data || { total_anchors: 0, history: [] };
  },

  // ── Officer Decisions ──
  recordDecision: async (
    payload: {
      bidder_id: string;
      tender_id: string;
      decision: "eligible" | "review" | "disqualified";
      reason: string;
      justification: string;
      officer_name?: string;
    },
    role?: string
  ): Promise<OfficerDecision> => {
    const res = await fetchAPI<OfficerDecision>(
      "/api/verification/decision",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      role
    );
    if (!res.data) throw new Error("Failed to record officer decision");
    return res.data;
  },

  getDecisions: async (tenderId: string): Promise<OfficerDecision[]> => {
    const res = await fetchAPI<OfficerDecision[]>(`/api/verification/decisions/${encodeURIComponent(tenderId)}`);
    return res.data || [];
  },

  // ── Scrutiny Report ──
  getScrutinyReport: async (tenderId: string): Promise<ScrutinyReport> => {
    const res = await fetchAPI<ScrutinyReport>(`/api/verification/report/${encodeURIComponent(tenderId)}`);
    if (!res.data) throw new Error("Failed to retrieve scrutiny report");
    return res.data;
  },

  // ── Copilot ──
  queryCopilot: async (query: string, tenderId?: string, bidderId?: string): Promise<CopilotResponse> => {
    const res = await fetchAPI<CopilotResponse>("/api/verification/copilot", {
      method: "POST",
      body: JSON.stringify({ query, tender_id: tenderId, bidder_id: bidderId }),
    });
    if (!res.data) throw new Error("No response from copilot");
    return res.data;
  },

  // ── Show-Cause & Documents ──
  getShowCauseNotice: async (bidderId: string, role = "officer"): Promise<ShowCauseNotice> => {
    const res = await fetchAPI<ShowCauseNotice>(`/api/verification/show-cause/${bidderId}`, undefined, role);
    if (!res.data) throw new Error("Failed to generate show-cause notice");
    return res.data;
  },

  getBidderDocuments: async (bidderId: string): Promise<DocumentVaultItem[]> => {
    const res = await fetchAPI<{ documents: DocumentVaultItem[] }>(`/api/verification/documents/${bidderId}`);
    return res.data?.documents || [];
  },

  // ── Graph ──
  getBidderGraph: async (bidderId: string): Promise<GraphData> => {
    const res = await fetchAPI<GraphData>(`/api/graph/bidder/${bidderId}`);
    if (!res.data) throw new Error("Failed to fetch bidder graph");
    return res.data;
  },

  getCollusionGraph: async (tenderId: string): Promise<GraphData> => {
    const res = await fetchAPI<GraphData>(`/api/graph/collusion/${encodeURIComponent(tenderId)}`);
    if (!res.data) throw new Error("Failed to fetch collusion graph");
    return res.data;
  },

  // ── Demo Reset ──
  resetDemoData: async () => {
    return fetchAPI<{ status: string; tender_id: string; timestamp: string }>("/api/verification/reset", {
      method: "POST",
    });
  },
};
