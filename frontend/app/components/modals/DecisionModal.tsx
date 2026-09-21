"use client";

import React, { useState } from "react";
import {
  X,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Loader2,
  FileText,
} from "lucide-react";
import { api } from "../../lib/api";
import { Button } from "../ui/Button";

interface DecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenderId: string;
  bidder: {
    bidder_id: string;
    entity_name: string;
    risk_level?: string;
    risk_score?: number;
    current_decision?: string;
  };
  onSuccess: () => void;
}

const REASONS = [
  "Full compliance verified with statutory registries",
  "Minor clarification needed on financial statements",
  "Shell company / filing history anomaly detected",
  "Directorship overlap / collusion ring identified",
  "Shared contact / bank / address indicators with competing bidder",
  "Statutory debarment or blacklisted entity under GFR 151",
  "Turnover or net worth threshold non-compliance",
  "Ineligible / invalid MSME claim or documentation",
  "Non-responsive to clarification / show-cause notice",
  "Adjudicated as fully compliant by procurement committee",
  "Other statutory ground",
];

export default function DecisionModal({
  isOpen,
  onClose,
  tenderId,
  bidder,
  onSuccess,
}: DecisionModalProps) {
  const [decision, setDecision] = useState<"eligible" | "review" | "disqualified">(
    (bidder.current_decision as "eligible" | "review" | "disqualified") || "review"
  );
  const [reason, setReason] = useState(REASONS[0]);
  const [justification, setJustification] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (decision === "disqualified" && (!justification || justification.trim().length < 5)) {
      setError("Disqualification under GFR 151 requires a recorded justification of at least 5 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await api.recordDecision({
        bidder_id: bidder.bidder_id,
        tender_id: tenderId,
        decision,
        reason,
        justification: justification.trim() || (decision === "eligible" ? "Adjudicated as compliant." : "Flagged for scrutiny."),
        officer_name: "officer_gem_01",
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to record decision on the server.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-white rounded-lg border border-slate-200 shadow-xl overflow-hidden flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-labelledby="decision-modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 id="decision-modal-title" className="text-base font-semibold text-slate-900">
                Record Procurement Adjudication
              </h2>
              <p className="text-xs text-slate-500 font-mono">
                GFR 151 Formal Decision • {bidder.bidder_id}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Entity Summary */}
          <div className="p-3 rounded-md bg-slate-50 border border-slate-200 flex items-center justify-between text-sm">
            <div>
              <div className="font-medium text-slate-900">{bidder.entity_name}</div>
              <div className="text-xs text-slate-500 font-mono mt-0.5">Tender ID: {tenderId}</div>
            </div>
            {bidder.risk_score !== undefined && (
              <div className="text-right">
                <div className="text-xs text-slate-500">Risk Score</div>
                <div className="text-sm font-semibold text-slate-900 font-mono">
                  {bidder.risk_score}/100
                </div>
              </div>
            )}
          </div>

          {/* Decision Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Adjudication Outcome <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-3 gap-2.5">
              <button
                type="button"
                onClick={() => setDecision("eligible")}
                className={`flex flex-col items-center justify-center p-3 rounded-md border text-center transition-all ${
                  decision === "eligible"
                    ? "border-emerald-500 bg-emerald-50/50 text-emerald-900 ring-1 ring-emerald-500 font-medium"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <CheckCircle2
                  className={`w-5 h-5 mb-1.5 ${
                    decision === "eligible" ? "text-emerald-600" : "text-slate-400"
                  }`}
                />
                <span className="text-xs font-semibold">Eligible</span>
                <span className="text-[10px] text-slate-500 mt-0.5">Clear for award</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision("review")}
                className={`flex flex-col items-center justify-center p-3 rounded-md border text-center transition-all ${
                  decision === "review"
                    ? "border-amber-500 bg-amber-50/50 text-amber-900 ring-1 ring-amber-500 font-medium"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <HelpCircle
                  className={`w-5 h-5 mb-1.5 ${
                    decision === "review" ? "text-amber-600" : "text-slate-400"
                  }`}
                />
                <span className="text-xs font-semibold">Under Review</span>
                <span className="text-[10px] text-slate-500 mt-0.5">Scrutiny required</span>
              </button>

              <button
                type="button"
                onClick={() => setDecision("disqualified")}
                className={`flex flex-col items-center justify-center p-3 rounded-md border text-center transition-all ${
                  decision === "disqualified"
                    ? "border-red-500 bg-red-50/50 text-red-900 ring-1 ring-red-500 font-medium"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <XCircle
                  className={`w-5 h-5 mb-1.5 ${
                    decision === "disqualified" ? "text-red-600" : "text-slate-400"
                  }`}
                />
                <span className="text-xs font-semibold">Disqualify</span>
                <span className="text-[10px] text-slate-500 mt-0.5">GFR 151 Debar</span>
              </button>
            </div>
          </div>

          {/* Reason Selection */}
          <div>
            <label
              htmlFor="decision-reason"
              className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
            >
              Primary Statutory Ground / Reason <span className="text-red-500">*</span>
            </label>
            <select
              id="decision-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full text-xs bg-white border border-slate-300 rounded-md px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {REASONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          {/* Justification */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="decision-justification"
                className="text-xs font-semibold text-slate-700 uppercase tracking-wider"
              >
                Officer Justification & Legal Basis{" "}
                {decision === "disqualified" && <span className="text-red-500">* (Mandatory)</span>}
              </label>
              <span className="text-[10px] text-slate-400 font-mono">
                {justification.length} chars
              </span>
            </div>
            <textarea
              id="decision-justification"
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Record the official rationale, evidence citations, or committee consensus for this determination..."
              className="w-full text-xs bg-white border border-slate-300 rounded-md p-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 leading-relaxed"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              This determination will be cryptographically anchored to the SHA-256 audit ledger and included in the Defensible Scrutiny Report.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 rounded-md bg-red-50 border border-red-200 flex items-start gap-2 text-xs text-red-800">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Footer actions */}
          <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span>Signed by Tender Officer (officer_gem_01)</span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" type="button" onClick={onClose} disabled={submitting}>
                Cancel
              </Button>
              <Button
                variant={decision === "disqualified" ? "danger" : "primary"}
                size="sm"
                type="submit"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Recording...
                  </>
                ) : (
                  "Record Decision"
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
