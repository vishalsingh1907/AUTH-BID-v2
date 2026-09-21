"use client";

import React from "react";
import {
  X,
  Scale,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Users,
  Building2,
  DollarSign,
  ShieldAlert,
  Info,
} from "lucide-react";
import { Badge } from "./ui/Badge";
import { formatCurrency } from "../lib/formatters";
import { getRiskBadgeVariant } from "../lib/risk";
import type { BidderSummary, VerificationResult, OfficerDecision } from "../lib/types";

interface BidderCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedIds: string[];
  onToggleSelectId: (id: string) => void;
  allBidders: BidderSummary[];
  allResults: VerificationResult[];
  decisions?: Record<string, OfficerDecision>;
  onViewDossier: (bidderId: string) => void;
}

export default function BidderCompareModal({
  isOpen,
  onClose,
  selectedIds,
  onToggleSelectId,
  allBidders = [],
  allResults = [],
  decisions = {},
  onViewDossier,
}: BidderCompareModalProps) {
  if (!isOpen) return null;

  // Merge bidders and results into normalized items
  const combinedList = allBidders.map((b) => {
    const res = allResults.find((r) => r.bidder_id === b.bidder_id);
    return {
      bidder_id: b.bidder_id,
      entity_name: b.entity_name,
      bid_amount: b.bid_amount,
      entity_type: b.entity_type,
      pan: b.pan,
      gstin: b.gstin,
      msme_category: b.msme_category,
      result: res,
    };
  });

  const selectedItems = combinedList.filter((item) => selectedIds.includes(item.bidder_id));
  const isMaxReached = selectedIds.length >= 4;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="compare-modal-title"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-300 w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center">
              <Scale size={20} />
            </div>
            <div>
              <h2 id="compare-modal-title" className="text-base font-bold text-slate-900 tracking-tight">
                Side-by-Side Bidder Intelligence Comparison
              </h2>
              <p className="text-xs text-slate-500">
                Multi-dimensional statutory, financial, and anti-collusion evaluation matrix (Select 1 to 4 bidders)
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 flex items-center justify-center text-slate-500 hover:text-slate-800 transition"
            aria-label="Close comparison modal"
          >
            <X size={16} />
          </button>
        </div>

        {/* Structured Bidder Selector Bar */}
        <div className="p-4 bg-slate-50/80 border-b border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-700 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Users size={14} className="text-blue-600" />
              Available Bidders ({allBidders.length})
            </span>
            <span
              className={`font-semibold text-xs px-2 py-0.5 rounded ${
                isMaxReached
                  ? "bg-amber-100 text-amber-900 border border-amber-300"
                  : "bg-blue-50 text-blue-800 border border-blue-200"
              }`}
            >
              {selectedIds.length} of 4 selected {isMaxReached && "(Maximum limit reached)"}
            </span>
          </div>

          {/* Selector Grid of Bidders */}
          {combinedList.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 bg-white rounded border border-slate-200">
              No bidder records loaded. Please ensure tender data is active.
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-36 overflow-y-auto p-1">
              {combinedList.map((item) => {
                const isSelected = selectedIds.includes(item.bidder_id);
                const disabled = !isSelected && isMaxReached;
                const riskLevel = item.result?.risk_score?.risk_level || "low";
                const riskScore = item.result?.risk_score?.overall_score;

                return (
                  <label
                    key={item.bidder_id}
                    className={`flex items-start gap-2 p-2 rounded-lg border cursor-pointer select-none transition-all text-xs ${
                      isSelected
                        ? "bg-blue-50/80 border-blue-400 ring-1 ring-blue-400 text-blue-950 font-medium"
                        : disabled
                        ? "opacity-50 cursor-not-allowed bg-slate-100 border-slate-200 text-slate-400"
                        : "bg-white border-slate-200 hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={disabled}
                      onChange={() => onToggleSelectId(item.bidder_id)}
                      className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-mono font-bold text-[11px]">{item.bidder_id}</span>
                        {riskScore !== undefined ? (
                          <span
                            className={`text-[9px] font-bold px-1 rounded ${
                              riskScore >= 70
                                ? "bg-red-100 text-red-700"
                                : riskScore >= 40
                                ? "bg-amber-100 text-amber-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {riskScore.toFixed(0)}
                          </span>
                        ) : null}
                      </div>
                      <div className="truncate text-[10px] text-slate-600 font-medium mt-0.5" title={item.entity_name}>
                        {item.entity_name}
                      </div>
                      <div className="text-[9px] text-slate-400 font-mono mt-0.5">
                        {formatCurrency(item.bid_amount)}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {/* Matrix Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedItems.length === 0 ? (
            <div className="text-center py-16 text-slate-400 space-y-2">
              <Scale size={40} className="mx-auto text-slate-300" />
              <p className="text-sm font-semibold text-slate-700">No Bidders Selected for Comparison</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Check 1 to 4 bidders from the selector grid above to analyze their technical compliance, risk scores, pricing, and collusion nexus side-by-side.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70">
                    <th className="p-3 text-left w-56 text-slate-600 uppercase tracking-wider font-bold text-[11px]">
                      Evaluation Dimension
                    </th>
                    {selectedItems.map((item) => {
                      const res = item.result;
                      const level = res?.risk_score?.risk_level || "low";
                      return (
                        <th key={item.bidder_id} className="p-3 text-left font-bold min-w-[220px]">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-bold">
                              {item.bidder_id}
                            </span>
                            {res?.risk_score ? (
                              <Badge variant={getRiskBadgeVariant(level)}>
                                {level.toUpperCase()} ({res.risk_score.overall_score.toFixed(0)}/100)
                              </Badge>
                            ) : (
                              <Badge variant="warning">PENDING</Badge>
                            )}
                          </div>
                          <p className="text-slate-900 font-bold text-xs truncate" title={item.entity_name}>
                            {item.entity_name}
                          </p>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {/* Quoted Bid Amount */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      <div className="flex items-center gap-1.5">
                        <DollarSign size={14} className="text-emerald-600" />
                        Quoted Bid Price
                      </div>
                    </td>
                    {selectedItems.map((item) => (
                      <td key={item.bidder_id} className="p-3 font-mono font-bold text-slate-900 text-sm">
                        {formatCurrency(item.bid_amount)}
                        <span className="block text-[10px] font-normal text-slate-400 mt-0.5">
                          PAN: {item.pan} • GSTIN: {item.gstin}
                        </span>
                      </td>
                    ))}
                  </tr>

                  {/* Composite Risk Score */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      Composite Risk Score
                    </td>
                    {selectedItems.map((item) => {
                      const score = item.result?.risk_score?.overall_score;
                      return (
                        <td key={item.bidder_id} className="p-3">
                          {score !== undefined ? (
                            <div>
                              <span
                                className={`font-mono font-black text-base ${
                                  score >= 70
                                    ? "text-red-700"
                                    : score >= 40
                                    ? "text-amber-700"
                                    : "text-emerald-700"
                                }`}
                              >
                                {score.toFixed(1)}
                              </span>
                              <span className="text-[11px] text-slate-400 font-mono"> / 100</span>
                              {item.result?.risk_score?.explanation && (
                                <p className="text-[10px] text-slate-600 mt-1 line-clamp-2">
                                  {item.result.risk_score.explanation}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Not evaluated</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Collusion Findings (Derived Dynamically from Anomalies) */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      <div className="flex items-center gap-1.5">
                        <ShieldAlert size={14} className="text-red-600" />
                        Collusion & Nexus Risk
                      </div>
                    </td>
                    {selectedItems.map((item) => {
                      const collusionAnomalies = (item.result?.anomalies || []).filter(
                        (a) =>
                          a.anomaly_type?.toLowerCase().includes("collusion") ||
                          a.title?.toLowerCase().includes("collusion") ||
                          (a.related_bidders && a.related_bidders.length > 0)
                      );

                      return (
                        <td key={item.bidder_id} className="p-3 text-xs">
                          {collusionAnomalies.length > 0 ? (
                            <div className="space-y-1">
                              {collusionAnomalies.map((a) => (
                                <div
                                  key={a.anomaly_id}
                                  className="p-1.5 bg-red-50 border border-red-200 rounded text-red-900 text-[11px]"
                                >
                                  <span className="font-bold block">{a.title}</span>
                                  {a.related_bidders && a.related_bidders.length > 0 && (
                                    <span className="text-[10px] text-red-700 font-mono">
                                      Nexus: {a.related_bidders.join(", ")}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-[11px]">
                              <CheckCircle2 size={12} /> No Direct Nexus Found
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Statutory Checks Passed vs Failed */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      Eligibility Pass Rate
                    </td>
                    {selectedItems.map((item) => {
                      const hard = item.result?.hard_eligibility || {};
                      const total = Object.keys(hard).length;
                      const passed = Object.values(hard).filter((v) => v === "pass").length;

                      return (
                        <td key={item.bidder_id} className="p-3 font-mono text-xs">
                          {total > 0 ? (
                            <div>
                              <span className="font-bold text-slate-800">
                                {passed} / {total} Checks Passed
                              </span>
                              <div className="w-full bg-slate-100 h-1.5 rounded-full mt-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    passed === total ? "bg-emerald-600" : "bg-amber-500"
                                  }`}
                                  style={{ width: `${(passed / total) * 100}%` }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Checks pending</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Failed / Warning Checks List */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      Failed / Warning Checks
                    </td>
                    {selectedItems.map((item) => {
                      const failed = (item.result?.compliance_checks || []).filter(
                        (c) => c.result !== "pass"
                      );

                      return (
                        <td key={item.bidder_id} className="p-3 text-xs">
                          {failed.length > 0 ? (
                            <ul className="space-y-1">
                              {failed.map((c) => (
                                <li
                                  key={c.check_id}
                                  className="text-[11px] text-red-700 flex items-start gap-1"
                                >
                                  <AlertTriangle size={12} className="shrink-0 mt-0.5 text-red-500" />
                                  <span>{c.check_name}: {c.details}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-emerald-700 font-medium text-[11px] flex items-center gap-1">
                              <CheckCircle2 size={12} /> All statutory checks passed
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* GFR 151 Officer Decision */}
                  <tr className="hover:bg-slate-50/50">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">
                      GFR 151 Adjudication
                    </td>
                    {selectedItems.map((item) => {
                      const dec = decisions[item.bidder_id];
                      return (
                        <td key={item.bidder_id} className="p-3 text-xs">
                          {dec ? (
                            <div>
                              <Badge
                                variant={
                                  dec.decision === "eligible"
                                    ? "success"
                                    : dec.decision === "disqualified"
                                    ? "danger"
                                    : "warning"
                                }
                              >
                                {dec.decision.toUpperCase()}
                              </Badge>
                              <div className="text-[11px] text-slate-700 mt-1 font-medium">{dec.reason}</div>
                              {dec.justification && (
                                <p className="text-[10px] text-slate-500 italic mt-0.5">
                                  {dec.justification}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Pending officer determination</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>

                  {/* Actions */}
                  <tr className="bg-slate-50/40">
                    <td className="p-3 font-semibold text-slate-700 bg-slate-50/40">Actions</td>
                    {selectedItems.map((item) => (
                      <td key={item.bidder_id} className="p-3">
                        <button
                          type="button"
                          onClick={() => {
                            onClose();
                            onViewDossier(item.bidder_id);
                          }}
                          className="w-full py-1.5 px-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-xs"
                        >
                          View Full Dossier
                        </button>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
