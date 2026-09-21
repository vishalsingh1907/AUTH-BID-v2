"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Scale,
  Check,
  AlertOctagon,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { formatCurrency } from "../../lib/formatters";
import { getRiskColor } from "../../lib/risk";
import type { VerificationResult, BidderSummary, OfficerDecision } from "../../lib/types";

interface TriageQueueProps {
  results: VerificationResult[];
  bidders: BidderSummary[];
  decisions: Record<string, OfficerDecision>;
  selectedCompareIds: string[];
  onToggleCompareId: (bidderId: string) => void;
  onSelectBidderForDossier: (result: VerificationResult) => void;
  onOpenDecisionModal: (bidderId: string) => void;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  results,
  bidders,
  decisions,
  selectedCompareIds,
  onToggleCompareId,
  onSelectBidderForDossier,
  onOpenDecisionModal,
}) => {
  if (results.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center shadow-xs">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-3">
          <Scale size={22} />
        </div>
        <h3 className="text-sm font-bold text-slate-800">
          No Bidders Match Active Triage Filters
        </h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Try clearing your search query or switching filter tabs to display all 12 submitted bids.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
              <th className="w-10 text-center py-3 px-2">
                <Scale size={13} className="mx-auto text-slate-400" />
              </th>
              <th className="py-3 px-3">Bidder Entity & ID</th>
              <th className="py-3 px-3">Commercial Bid</th>
              <th className="py-3 px-3">Compliance & Risk</th>
              <th className="py-3 px-3">Risk Level</th>
              <th className="py-3 px-3">Hard Eligibility</th>
              <th className="py-3 px-3">Anomalies</th>
              <th className="py-3 px-3">Officer Adjudication</th>
              <th className="py-3 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {results.map((r) => {
              const bidderMeta = bidders.find((b) => b.bidder_id === r.bidder_id);
              const score = r.risk_score?.overall_score || 0;
              const complianceScore = (r.risk_score as any)?.compliance_score ?? Math.max(0, 100 - score);
              const level = r.risk_score?.risk_level || "low";
              const decisionRecord = decisions[r.bidder_id];
              const decision = decisionRecord?.decision;
              const isChecked = selectedCompareIds.includes(r.bidder_id);

              const passCount = Object.values(r.hard_eligibility || {}).filter((v) => v === "pass").length;
              const failCount = Object.values(r.hard_eligibility || {}).filter((v) => v === "fail").length;

              return (
                <tr
                  key={r.bidder_id}
                  onClick={() => onSelectBidderForDossier(r)}
                  className="group hover:bg-slate-50/80 transition-colors cursor-pointer"
                >
                  {/* Compare Checkbox */}
                  <td className="text-center py-3.5 px-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggleCompareId(r.bidder_id)}
                      title={isChecked ? "Remove from matrix comparison" : "Add to matrix comparison (up to 4)"}
                      className="rounded border-slate-300 text-slate-900 focus:ring-slate-400 cursor-pointer"
                    />
                  </td>

                  {/* Bidder Profile */}
                  <td className="py-3.5 px-3">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                        {r.entity_name}
                      </span>
                      {bidderMeta?.entity_type && (
                        <span className="text-[10px] px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded font-medium">
                          {bidderMeta.entity_type}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] font-mono text-slate-400 mt-0.5">
                      ID: {r.bidder_id} {bidderMeta?.trade_name ? `• ${bidderMeta.trade_name}` : ""}
                    </p>
                  </td>

                  {/* Quoted Bid */}
                  <td className="py-3.5 px-3 font-mono font-semibold text-slate-800 text-xs">
                    {formatCurrency(bidderMeta?.bid_amount || 0)}
                  </td>

                  {/* Compliance & Risk Score */}
                  <td className="py-3.5 px-3">
                    <div className="space-y-1 min-w-[125px]">
                      <div className="flex items-center justify-between gap-1.5">
                        <span className="font-mono font-bold text-xs text-slate-900">
                          {complianceScore.toFixed(0)}% Compliant
                        </span>
                        <span
                          className="font-mono text-[10px] font-bold"
                          style={{ color: getRiskColor(level) }}
                        >
                          Risk: {score.toFixed(1)}
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            complianceScore >= 80
                              ? "bg-emerald-500"
                              : complianceScore >= 50
                              ? "bg-amber-500"
                              : "bg-red-500"
                          }`}
                          style={{ width: `${Math.max(5, complianceScore)}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Risk Level Badge */}
                  <td className="py-3.5 px-3">
                    <Badge
                      variant={level === "critical" || level === "high" ? "danger" : level === "medium" ? "warning" : "success"}
                      size="sm"
                      dot
                    >
                      {level.toUpperCase()}
                    </Badge>
                  </td>

                  {/* Hard Eligibility */}
                  <td className="py-3.5 px-3">
                    <div className="flex items-center gap-1 font-mono text-xs">
                      <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200/60">
                        {passCount}P
                      </span>
                      {failCount > 0 && (
                        <span className="font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200/60">
                          {failCount}F
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Anomalies */}
                  <td className="py-3.5 px-3">
                    {r.anomalies && r.anomalies.length > 0 ? (
                      <span className="inline-flex items-center gap-1 font-semibold text-[11px] px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200/60">
                        <AlertTriangle size={11} />
                        {r.anomalies.length} Flagged
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 font-medium text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                        <Check size={11} /> Clean
                      </span>
                    )}
                  </td>

                  {/* Officer Adjudication */}
                  <td className="py-3.5 px-3" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onOpenDecisionModal(r.bidder_id)}
                      className="cursor-pointer transition hover:opacity-80 text-left"
                      title="Click to record or modify official officer decision"
                    >
                      {decision === "eligible" && (
                        <Badge variant="success" size="sm">
                          Qualified L1
                        </Badge>
                      )}
                      {decision === "review" && (
                        <Badge variant="warning" size="sm">
                          In Scrutiny
                        </Badge>
                      )}
                      {decision === "disqualified" && (
                        <Badge variant="danger" size="sm">
                          Disqualified
                        </Badge>
                      )}
                      {!decision && (
                        <span className="text-[11px] text-slate-400 italic hover:text-slate-600">
                          Pending Decision →
                        </span>
                      )}
                    </button>
                  </td>

                  {/* Action Link */}
                  <td className="py-3.5 px-3 text-right">
                    <div className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 group-hover:text-blue-800">
                      <span>Dossier</span>
                      <ChevronRight size={14} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TriageQueue;
