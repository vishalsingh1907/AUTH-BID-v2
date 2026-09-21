"use client";

import React, { useState, useEffect } from "react";
import {
  Printer,
  Download,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  FileCheck,
  Scale,
  Award,
  Users,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Hash,
} from "lucide-react";
import { api } from "../../lib/api";
import { ScrutinyReport, VerificationResult } from "../../lib/types";
import { formatCurrency, formatDateTime, truncateHash } from "../../lib/formatters";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface ScrutinyReportViewProps {
  tenderId: string;
}

export default function ScrutinyReportView({ tenderId }: ScrutinyReportViewProps) {
  const [report, setReport] = useState<ScrutinyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getScrutinyReport(tenderId);
      if (res) {
        setReport(res);
      } else {
        setError("Scrutiny report could not be compiled for this tender.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load scrutiny report.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [tenderId]);

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJSON = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scrutiny_report_${tenderId}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-white rounded-lg border border-slate-200 text-slate-500 space-y-3">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-600">Compiling official scrutiny report from live verification data...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border border-slate-200 max-w-xl mx-auto my-8">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-900 mb-1">Report Compilation Failed</h3>
        <p className="text-xs text-slate-600 mb-4">{error || "No report data returned."}</p>
        <Button variant="outline" size="sm" onClick={fetchReport}>
          Retry Compilation
        </Button>
      </div>
    );
  }

  const { summary, clean_bidders = [], disqualified_bidders = [] } = report;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Action Toolbar (Hidden during print) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 print:hidden">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Scale className="w-4 h-4 text-blue-600" />
            Defensible Tender Scrutiny Report
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            GFR 151 compliance summary, cross-bidder risk findings, and recorded officer adjudications.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchReport}>
            <RotateCcw className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadJSON}>
            <Download className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
            Export JSON
          </Button>
          <Button variant="primary" size="sm" onClick={handlePrint}>
            <Printer className="w-3.5 h-3.5 mr-1.5" />
            Print / PDF
          </Button>
        </div>
      </div>

      {/* Printable Report Document Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-8 shadow-sm space-y-8 print:p-0 print:border-none print:shadow-none text-slate-900 font-sans">
        {/* Official Header */}
        <div className="border-b-2 border-slate-900 pb-6 text-center space-y-2">
          <div className="text-[11px] font-bold uppercase tracking-widest text-slate-600">
            Government e-Marketplace (GeM) • Central Public Procurement Portal
          </div>
          <h1 className="text-xl font-bold uppercase tracking-tight text-slate-900">
            Tender Scrutiny & Due Diligence Determination Report
          </h1>
          <div className="text-xs text-slate-600">
            {report.committee_authority || "GeM Technical Scrutiny Sub-Committee"} • GFR 2017 Rule 151
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-md border border-slate-200 text-xs print:bg-transparent">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Tender ID</span>
            <span className="font-mono font-bold text-slate-900">{report.tender_id}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Estimated Value</span>
            <span className="font-mono font-medium text-slate-800">{formatCurrency(report.estimated_value)}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Generated Timestamp</span>
            <span className="font-mono text-slate-800">{formatDateTime(report.generated_at)}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Audit Ledger Root</span>
            <span className="font-mono text-slate-800 text-[11px]">{truncateHash(summary.root_hash, 8)}</span>
          </div>
        </div>

        {/* Executive Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="p-3 rounded border border-slate-200 bg-white">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">Total Bidders</div>
            <div className="text-lg font-bold font-mono text-slate-900 mt-1">{summary.total_bidders}</div>
          </div>
          <div className="p-3 rounded border border-emerald-200 bg-emerald-50/50">
            <div className="text-[10px] text-emerald-700 uppercase font-semibold">Qualified for Financial Eval</div>
            <div className="text-lg font-bold font-mono text-emerald-800 mt-1">{summary.recommended_for_financial_evaluation}</div>
          </div>
          <div className="p-3 rounded border border-red-200 bg-red-50/50">
            <div className="text-[10px] text-red-700 uppercase font-semibold">Disqualified / Flagged</div>
            <div className="text-lg font-bold font-mono text-red-800 mt-1">{summary.disqualified_or_flagged}</div>
          </div>
          <div className="p-3 rounded border border-slate-200 bg-white">
            <div className="text-[10px] text-slate-500 uppercase font-semibold">Ledger Verification</div>
            <div className="text-sm font-bold font-mono text-emerald-700 mt-1">
              {summary.cryptographic_verification}
            </div>
          </div>
        </div>

        {/* Section 1: Clean / Recommended Bidders Table */}
        <div className="space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-emerald-800 pb-1 border-b border-emerald-300 flex items-center justify-between">
            <span>Section 1: Qualified Bidders Recommended for Financial Opening ({clean_bidders.length})</span>
            <span className="text-[10px] font-normal text-slate-500">Fully Compliant</span>
          </h2>

          {clean_bidders.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 border border-slate-200 rounded">
              No bidders currently meet full clean compliance criteria without flags.
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Bidder ID</th>
                    <th className="py-2.5 px-3">Entity Name</th>
                    <th className="py-2.5 px-3 text-center">Risk Score</th>
                    <th className="py-2.5 px-3">Eligibility Determination</th>
                    <th className="py-2.5 px-3">AI Synthesis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {clean_bidders.map((b: VerificationResult) => (
                    <tr key={b.bidder_id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900 whitespace-nowrap">
                        {b.bidder_id}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">{b.entity_name}</td>
                      <td className="py-2.5 px-3 text-center font-mono font-bold">
                        <span className="px-2 py-0.5 rounded text-xs bg-emerald-50 text-emerald-800">
                          {b.risk_score?.overall_score ?? 0}/100
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant="success">QUALIFIED</Badge>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600 text-[11px] leading-relaxed">
                        {b.system_recommendation || b.ai_recommendation || "Verified compliant across statutory registries."}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Section 2: Flagged / Disqualified Bidders Table */}
        <div className="space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-red-800 pb-1 border-b border-red-300 flex items-center justify-between">
            <span>Section 2: Flagged or Disqualified Bidders ({disqualified_bidders.length})</span>
            <span className="text-[10px] font-normal text-slate-500">Statutory Scrutiny Required</span>
          </h2>

          {disqualified_bidders.length === 0 ? (
            <div className="p-4 text-center text-xs text-slate-500 border border-slate-200 rounded">
              No high or critical-risk bidders flagged.
            </div>
          ) : (
            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Bidder ID</th>
                    <th className="py-2.5 px-3">Entity Name</th>
                    <th className="py-2.5 px-3 text-center">Risk Score</th>
                    <th className="py-2.5 px-3">Status / Level</th>
                    <th className="py-2.5 px-3">Detected Anomalies & Findings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {disqualified_bidders.map((b: VerificationResult) => (
                    <tr key={b.bidder_id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900 whitespace-nowrap">
                        {b.bidder_id}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-800">{b.entity_name}</td>
                      <td className="py-2.5 px-3 text-center font-mono font-bold">
                        <span className="px-2 py-0.5 rounded text-xs bg-red-50 text-red-700">
                          {b.risk_score?.overall_score ?? 0}/100
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant="danger">{b.risk_score?.risk_level?.toUpperCase() || "FLAGGED"}</Badge>
                      </td>
                      <td className="py-2.5 px-3 text-slate-700 text-[11px] leading-relaxed">
                        {b.anomalies && b.anomalies.length > 0 ? (
                          <ul className="list-disc list-inside space-y-0.5 text-red-700">
                            {b.anomalies.map((a, idx) => (
                              <li key={idx}>
                                <span className="font-semibold">{a.title}:</span> {a.description}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-slate-500 italic">Flagged under composite risk model</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Attestation & Committee Signature Block */}
        <div className="pt-8 border-t-2 border-slate-300 space-y-6">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-800">
            Section 3: Committee Attestation & Verification Stamp
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 pt-6 text-center text-xs">
            <div className="space-y-4">
              <div className="h-12 border-b border-dashed border-slate-400" />
              <div>
                <div className="font-bold text-slate-900">Tender Officer / Convener</div>
                <div className="text-slate-500 text-[11px]">officer_gem_01</div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="h-12 border-b border-dashed border-slate-400" />
              <div>
                <div className="font-bold text-slate-900">Technical Scrutiny Member</div>
                <div className="text-slate-500 text-[11px]">Member (Technical)</div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="h-12 border-b border-dashed border-slate-400" />
              <div>
                <div className="font-bold text-slate-900">Financial Advisor / Director</div>
                <div className="text-slate-500 text-[11px]">Member (Finance)</div>
              </div>
            </div>
          </div>

          <div className="p-3 bg-slate-100 rounded text-center text-[10px] text-slate-600 font-mono">
            Cryptographically Anchored to SHA-256 Ledger • Stamp: {summary.root_hash} • Generated via AuthBid v2.0
          </div>
        </div>
      </div>
    </div>
  );
}
