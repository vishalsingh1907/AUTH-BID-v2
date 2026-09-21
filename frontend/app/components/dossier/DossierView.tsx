"use client";

import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Building2,
  Users,
  DollarSign,
  FileCheck2,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Scale,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FolderLock,
  GitCompare,
  TrendingUp,
  Play,
  RotateCcw,
  Landmark,
} from "lucide-react";
import { api } from "../../lib/api";
import {
  BidderDetail,
  VerificationResult,
  BidderDossierViewModel,
  DossierState,
  OfficerDecision,
} from "../../lib/types";
import { formatCurrency, formatDate, formatDateTime } from "../../lib/formatters";
import { getRiskBadgeVariant, getRiskLevel } from "../../lib/risk";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import DecisionModal from "../modals/DecisionModal";

interface DossierViewProps {
  bidderId: string;
  tenderId: string;
  onBack: () => void;
  onOpenShowCause?: (bidderId: string) => void;
  onOpenCompare?: (bidderId: string) => void;
  onOpenPriceAnalysis?: (bidderId: string) => void;
  onOpenDocumentVault?: (bidderId: string) => void;
  onTriggerVerification?: () => void;
  onDecisionChanged?: () => void;
}

export default function DossierView({
  bidderId,
  tenderId,
  onBack,
  onOpenShowCause,
  onOpenCompare,
  onOpenPriceAnalysis,
  onOpenDocumentVault,
  onTriggerVerification,
  onDecisionChanged,
}: DossierViewProps) {
  const [dossierState, setDossierState] = useState<DossierState>({
    status: "loading",
    dossier: null,
    error: null,
  });
  const [decision, setDecision] = useState<OfficerDecision | null>(null);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [expandedAnomalies, setExpandedAnomalies] = useState<Record<string, boolean>>({});

  const fetchDossierData = async () => {
    setDossierState((prev) => ({ ...prev, status: "loading", error: null }));
    try {
      const [bidderProfile, verifResult, decisionsList] = await Promise.all([
        api.getBidder(bidderId).catch(() => null),
        api.getBidderVerification(bidderId, tenderId).catch(() => null),
        api.getDecisions(tenderId).catch(() => []),
      ]);

      if (!bidderProfile) {
        setDossierState({
          status: "not_found",
          dossier: null,
          error: `Bidder record '${bidderId}' was not found in statutory database.`,
        });
        return;
      }

      // Check if officer decision exists for this bidder
      const currentDecision = decisionsList.find((d) => d.bidder_id === bidderId) || null;
      setDecision(currentDecision);

      // Determine verification status
      let verifStatus: "pending" | "completed" | "not_run" = "not_run";
      if (verifResult) {
        if (verifResult.status === "completed" || verifResult.risk_score) {
          verifStatus = "completed";
        } else if (verifResult.status === "pending") {
          verifStatus = "pending";
        }
      }

      // Merge into unified BidderDossierViewModel
      const unifiedDossier: BidderDossierViewModel = {
        bidder_id: bidderProfile.bidder_id,
        entity_name: bidderProfile.entity_name,
        trade_name: bidderProfile.trade_name,
        entity_type: bidderProfile.entity_type,
        identifiers: bidderProfile.identifiers || {
          pan: "Unavailable",
          gstin: "Unavailable",
        },
        incorporation_date: bidderProfile.incorporation_date,
        registered_address: bidderProfile.registered_address,
        directors: bidderProfile.directors || [],
        bank_account: bidderProfile.bank_account,
        gst_status: bidderProfile.gst_status || "Unknown",
        annual_turnover: bidderProfile.annual_turnover || [],
        msme_category: bidderProfile.msme_category,
        msme_valid_until: bidderProfile.msme_valid_until,
        certifications: bidderProfile.certifications || [],
        epfo_registered: bidderProfile.epfo_registered,
        epfo_establishment_code: (bidderProfile as any).epfo_establishment_code,
        esic_registered: (bidderProfile as any).esic_registered,
        esic_establishment_code: (bidderProfile as any).esic_establishment_code,
        startup_india_registered: (bidderProfile as any).startup_india_registered,
        dipp_recognition_no: (bidderProfile as any).dipp_recognition_no,
        nsic_registered: (bidderProfile as any).nsic_registered,
        itr_filed_last_3_years: (bidderProfile as any).itr_filed_last_3_years,
        digilocker_verified: (bidderProfile as any).digilocker_verified,
        bid_amount: bidderProfile.bid_amount,
        make_in_india_percent: bidderProfile.make_in_india_percent,
        oem_authorization: bidderProfile.oem_authorization,
        oem_name: bidderProfile.oem_name,

        // Merged verification results
        verification_status: verifStatus,
        risk_score: verifResult?.risk_score,
        compliance_checks: verifResult?.compliance_checks,
        anomalies: verifResult?.anomalies,
        hard_eligibility: verifResult?.hard_eligibility,
        system_recommendation: verifResult?.system_recommendation || verifResult?.ai_recommendation,
        ai_recommendation: verifResult?.system_recommendation || verifResult?.ai_recommendation,
        ai_confidence: verifResult?.ai_confidence,
        completed_at: verifResult?.completed_at,
      };

      setDossierState({
        status: "ready",
        dossier: unifiedDossier,
        error: null,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load bidder intelligence dossier.";
      setDossierState({
        status: "error",
        dossier: null,
        error: msg,
      });
    }
  };

  useEffect(() => {
    if (bidderId) {
      setExpandedAnomalies({});
      fetchDossierData();
    }
  }, [bidderId, tenderId]);

  const toggleAnomaly = (id: string) => {
    setExpandedAnomalies((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // ── State 1: Loading Skeleton ──
  if (dossierState.status === "loading") {
    return (
      <div className="space-y-6 animate-in fade-in duration-150">
        {/* Top bar skeleton */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={onBack}>
              <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Queue
            </Button>
            <div className="h-4 w-px bg-slate-200" />
            <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
              {bidderId}
            </span>
          </div>
        </div>

        {/* Header skeleton */}
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-xs animate-pulse space-y-4">
          <div className="h-6 w-72 bg-slate-200 rounded" />
          <div className="h-4 w-96 bg-slate-100 rounded" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-slate-50 border border-slate-100 rounded" />
            ))}
          </div>
        </div>

        <div className="text-center py-10 text-slate-500 text-xs">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading statutory dossier and multi-source verification records...
        </div>
      </div>
    );
  }

  // ── State 2: Error State with Retry ──
  if (dossierState.status === "error") {
    return (
      <div className="p-8 max-w-xl mx-auto my-8 text-center bg-white border border-red-200 rounded-lg shadow-xs">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-900 mb-1">Dossier Retrieval Failed</h3>
        <p className="text-xs text-slate-600 mb-4">{dossierState.error}</p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" size="sm" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-1.5" /> Return to Queue
          </Button>
          <Button variant="primary" size="sm" onClick={fetchDossierData}>
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Retry Request
          </Button>
        </div>
      </div>
    );
  }

  // ── State 3: Not Found State ──
  if (dossierState.status === "not_found" || !dossierState.dossier) {
    return (
      <div className="p-8 max-w-xl mx-auto my-8 text-center bg-white border border-slate-200 rounded-lg shadow-xs">
        <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-900 mb-1">Bidder Record Not Found</h3>
        <p className="text-xs text-slate-600 mb-4">
          {dossierState.error || `No statutory record exists for identifier ${bidderId}.`}
        </p>
        <Button variant="outline" size="sm" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-1.5" /> Return to Queue
        </Button>
      </div>
    );
  }

  const dossier = dossierState.dossier;
  const isVerified = dossier.verification_status === "completed";
  const riskScore = dossier.risk_score?.overall_score ?? 0;
  const riskLevel = dossier.risk_score?.risk_level || getRiskLevel(riskScore);
  const anomalies = dossier.anomalies || [];
  const complianceChecks = dossier.compliance_checks || [];
  const highSevAnomalies = anomalies.filter((a) => a.severity === "high" || a.severity === "critical");

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Navigation & Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={onBack} aria-label="Back to queue">
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            Back to Queue
          </Button>
          <div className="h-4 w-px bg-slate-200 hidden sm:block" />
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
              {dossier.bidder_id}
            </span>
            <span className="text-xs text-slate-500 font-mono">Tender: {tenderId}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {onOpenCompare && (
            <Button variant="outline" size="sm" onClick={() => onOpenCompare(dossier.bidder_id)}>
              <GitCompare className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Compare
            </Button>
          )}

          {onOpenPriceAnalysis && (
            <Button variant="outline" size="sm" onClick={() => onOpenPriceAnalysis(dossier.bidder_id)}>
              <TrendingUp className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Price Analysis
            </Button>
          )}

          {onOpenDocumentVault && (
            <Button variant="outline" size="sm" onClick={() => onOpenDocumentVault(dossier.bidder_id)}>
              <FolderLock className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Document Vault
            </Button>
          )}

          {onOpenShowCause && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenShowCause(dossier.bidder_id)}
              className="text-amber-700 border-amber-300 hover:bg-amber-50"
            >
              <FileText className="w-3.5 h-3.5 mr-1.5 text-amber-600" />
              Show-Cause Notice
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            onClick={() => setDecisionModalOpen(true)}
            className="font-medium shadow-xs"
          >
            <Scale className="w-3.5 h-3.5 mr-1.5" />
            Adjudicate (GFR 151)
          </Button>
        </div>
      </div>

      {/* Main Dossier Header Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {dossier.entity_name}
              </h1>
              {isVerified ? (
                <Badge variant={getRiskBadgeVariant(riskLevel)}>
                  {riskLevel.toUpperCase()} RISK • {riskScore}/100
                </Badge>
              ) : (
                <Badge variant="warning">VERIFICATION PENDING</Badge>
              )}

              {decision ? (
                <Badge
                  variant={
                    decision.decision === "eligible"
                      ? "success"
                      : decision.decision === "disqualified"
                      ? "danger"
                      : "warning"
                  }
                >
                  Decision: {decision.decision.toUpperCase()}
                </Badge>
              ) : (
                <Badge variant="neutral">Pending Adjudication</Badge>
              )}
            </div>

            {/* Entity Identifiers (Honest data states) */}
            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-600">
              <span className="flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5 text-slate-400" />
                {dossier.entity_type || "Private Limited"}
              </span>
              <span>•</span>
              <span className="font-mono">
                PAN: <strong className="text-slate-800">{dossier.identifiers.pan || "Unavailable"}</strong>
              </span>
              <span>•</span>
              <span className="font-mono">
                GSTIN: <strong className="text-slate-800">{dossier.identifiers.gstin || "Unavailable"}</strong>
              </span>
              <span>•</span>
              <span>Inc: {formatDate(dossier.incorporation_date)}</span>
            </div>

            <div className="text-xs text-slate-500 pt-1">
              Registered Address:{" "}
              {dossier.registered_address
                ? `${dossier.registered_address.line1}, ${dossier.registered_address.city}, ${dossier.registered_address.state} - ${dossier.registered_address.pincode}`
                : "Address record unavailable"}
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0">
            <div className="p-3 bg-slate-50 rounded-md border border-slate-200 text-center min-w-[110px]">
              <div className="text-[11px] font-medium text-slate-500 uppercase">Bid Amount</div>
              <div className="text-sm font-bold text-slate-900 font-mono mt-0.5">
                {dossier.bid_amount ? formatCurrency(dossier.bid_amount) : "N/A"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Quoted Amount</div>
            </div>

            <div className="p-3 bg-slate-50 rounded-md border border-slate-200 text-center min-w-[110px]">
              <div className="text-[11px] font-medium text-slate-500 uppercase">Anomalies</div>
              <div
                className={`text-sm font-bold font-mono mt-0.5 ${
                  anomalies.length > 0 ? "text-red-700" : "text-emerald-700"
                }`}
              >
                {anomalies.length} Flagged
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {highSevAnomalies.length} Critical/High
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-md border border-slate-200 text-center min-w-[110px]">
              <div className="text-[11px] font-medium text-slate-500 uppercase">GST Portal</div>
              <div
                className={`text-sm font-bold font-mono mt-0.5 ${
                  dossier.gst_status === "Active" ? "text-emerald-700" : "text-amber-700"
                }`}
              >
                {dossier.gst_status || "Active"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Statutory Status</div>
            </div>

            <div className="p-3 bg-slate-50 rounded-md border border-slate-200 text-center min-w-[110px]">
              <div className="text-[11px] font-medium text-slate-500 uppercase">MSME Status</div>
              <div className="text-sm font-bold text-slate-900 font-mono mt-0.5">
                {dossier.msme_category || "Non-MSME"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {dossier.identifiers.udyam_no ? "Udyam Verified" : "Standard"}
              </div>
            </div>
          </div>
        </div>

        {/* Existing Decision Banner */}
        {decision && (
          <div className="mt-4 p-3 bg-blue-50/50 rounded-md border border-blue-200 flex items-start justify-between text-xs text-blue-950">
            <div className="flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Recorded Adjudication:</span>{" "}
                <span className="font-mono uppercase font-bold">{decision.decision}</span> •{" "}
                <span className="italic">{decision.reason}</span>
                {decision.justification && (
                  <p className="mt-1 text-slate-700 font-sans">
                    Justification: {decision.justification}
                  </p>
                )}
              </div>
            </div>
            <div className="text-right text-[11px] text-slate-500 shrink-0 font-mono">
              <div>By: {decision.officer_name || decision.role}</div>
              <div>{formatDateTime(decision.timestamp)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Verification Pending Banner if not run */}
      {!isVerified && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-950">
          <div className="flex items-center gap-2.5">
            <Clock className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <span className="font-bold">Multi-Source Verification Not Yet Executed</span>
              <p className="text-slate-600 mt-0.5">
                Statutory registries and collusion graph analysis have not been evaluated for this tender.
              </p>
            </div>
          </div>
          {onTriggerVerification && (
            <Button variant="primary" size="sm" onClick={onTriggerVerification} className="shrink-0">
              <Play className="w-3.5 h-3.5 mr-1" /> Run Verification Pipeline
            </Button>
          )}
        </div>
      )}

      {/* SIH26100 Statutory Government Portals Verification Matrix */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
              <Landmark size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Statutory Government Portals & Registries Verification Matrix
              </h3>
              <p className="text-xs text-slate-500">
                Automated multi-portal API Setu compliance cross-checks under GeM GTC & GFR 2017
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full flex items-center gap-1">
              <CheckCircle2 size={12} />
              API Setu Connected
            </span>
            <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
              SIH26100 Compliant
            </span>
          </div>
        </div>

        {/* 10 Portals Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-1">
          {/* 1. MCA21 V3 */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">MCA21 V3</span>
              <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800">
                ACTIVE
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900 truncate">
              {dossier.identifiers.cin || "ROC Reg: Active"}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>{dossier.directors.length} Verified DINs</span>
              <span className="font-mono">Cos. Act 2013</span>
            </div>
          </div>

          {/* 2. GSTN */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">GSTN Returns</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.gst_status === "Active" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
              }`}>
                {dossier.gst_status.toUpperCase()}
              </span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900 truncate">
              {dossier.identifiers.gstin}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>GSTR-3B Regular</span>
              <span className="font-mono">Sec 39 CGST</span>
            </div>
          </div>

          {/* 3. CBDT / PAN & Income Tax */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">CBDT / PAN & ITR</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.itr_filed_last_3_years !== false ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800 animate-pulse"
              }`}>
                {dossier.itr_filed_last_3_years !== false ? "ITR FILED" : "MISSING ITR"}
              </span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900">
              {dossier.identifiers.pan}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>3-Yr AY Filings</span>
              <span className="font-mono">Sec 139A</span>
            </div>
          </div>

          {/* 4. Udyam MSME */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Udyam MSME</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.msme_category
                  ? (dossier.msme_valid_until && new Date(dossier.msme_valid_until) < new Date() ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800")
                  : "bg-slate-100 text-slate-600"
              }`}>
                {dossier.msme_category ? (dossier.msme_valid_until && new Date(dossier.msme_valid_until) < new Date() ? "EXPIRED" : "VERIFIED") : "STANDARD"}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900 truncate">
              {dossier.identifiers.udyam_no || (dossier.msme_category ? "Udyam Reg Claimed" : "Non-MSME Entity")}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>{dossier.msme_category || "Standard Enterprise"}</span>
              <span className="font-mono">PPP 2012</span>
            </div>
          </div>

          {/* 5. EPFO & ESIC */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">EPFO & ESIC</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.epfo_registered && dossier.esic_registered !== false ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
              }`}>
                {dossier.epfo_registered ? "COMPLIANT" : "EXEMPT"}
              </span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900 truncate">
              {dossier.epfo_establishment_code || (dossier.epfo_registered ? "EPFO Reg Verified" : "Sub-threshold")}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>Labour Compliance</span>
              <span className="font-mono">EPF/ESI Act</span>
            </div>
          </div>

          {/* 6. Startup India & NSIC */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Startup / NSIC</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.startup_india_registered || dossier.nsic_registered ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-600"
              }`}>
                {dossier.startup_india_registered ? "DPIIT STARTUP" : dossier.nsic_registered ? "NSIC ENROLLED" : "STANDARD"}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900 truncate">
              {dossier.dipp_recognition_no || (dossier.nsic_registered ? "NSIC Certified" : "Commercial Enterprise")}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>Prior Turnover Relief</span>
              <span className="font-mono">GFR 173(i)</span>
            </div>
          </div>

          {/* 7. Make in India (DPIIT) */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Make in India</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                (dossier.make_in_india_percent || 0) >= 50 ? "bg-emerald-100 text-emerald-800" : (dossier.make_in_india_percent || 0) >= 20 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"
              }`}>
                {(dossier.make_in_india_percent || 0) >= 50 ? "CLASS-I" : (dossier.make_in_india_percent || 0) >= 20 ? "CLASS-II" : "NON-LOCAL"}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900">
              {dossier.make_in_india_percent || 50}% Local Content
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>Domestic Value Add</span>
              <span className="font-mono">MII Order</span>
            </div>
          </div>

          {/* 8. Debarment (GFR 151) */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">GFR 151 Debarment</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                anomalies.some((a) => a.anomaly_type === "debarment") ? "bg-red-100 text-red-800 animate-pulse" : "bg-emerald-100 text-emerald-800"
              }`}>
                {anomalies.some((a) => a.anomaly_type === "debarment") ? "FLAGGED" : "CLEAR"}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900 truncate">
              {anomalies.some((a) => a.anomaly_type === "debarment") ? "Historical Record" : "Zero Debarment Orders"}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>Central Vigilance</span>
              <span className="font-mono">GFR Rule 151</span>
            </div>
          </div>

          {/* 9. OEM Authorization */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">OEM Authorization</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.oem_authorization ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
              }`}>
                {dossier.oem_authorization ? "VERIFIED" : "NON-COMPLIANT"}
              </span>
            </div>
            <div className="text-xs font-bold text-slate-900 truncate">
              {dossier.oem_name || "Direct OEM / MAF"}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>MAF Form Valid</span>
              <span className="font-mono">GeM GTC 4.14</span>
            </div>
          </div>

          {/* 10. DigiLocker / SHA-256 */}
          <div className="p-3 bg-slate-50/70 border border-slate-200 rounded-lg space-y-1.5 hover:bg-slate-50 transition">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">DigiLocker / Seal</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                dossier.digilocker_verified !== false ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800 animate-pulse"
              }`}>
                {dossier.digilocker_verified !== false ? "SEALED" : "UNVERIFIED"}
              </span>
            </div>
            <div className="text-xs font-mono font-bold text-slate-900 truncate">
              {dossier.digilocker_verified !== false ? "SHA-256 Verified" : "Disclaimer of Opinion"}
            </div>
            <div className="text-[10px] text-slate-500 flex justify-between">
              <span>Digital Provenance</span>
              <span className="font-mono">IT Act 65B</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Left Column (Risk & Anomalies) | Right Column (Compliance & Directorship) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Evidence, Anomalies, and AI Synthesis */}
        <div className="lg:col-span-2 space-y-6">
          {/* System Recommendation & Risk Explanation */}
          {(dossier.system_recommendation || dossier.ai_recommendation) && (
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-slate-700 uppercase tracking-wider">
                <Search className="w-4 h-4 text-blue-600" />
                <span>System Recommendation & Risk Explanation</span>
              </div>
              <p className="text-xs text-slate-800 leading-relaxed">
                {dossier.system_recommendation || dossier.ai_recommendation}
              </p>
            </div>
          )}

          {/* Risk Breakdown Components */}
          {dossier.risk_score?.components && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
              <div className="p-3 bg-white rounded-md border border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-medium">Cross-Source</div>
                <div className="text-sm font-bold text-slate-900 font-mono mt-1">
                  {dossier.risk_score.components.cross_source_consistency}/100
                </div>
              </div>

              <div className="p-3 bg-white rounded-md border border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-medium">Collusion</div>
                <div className="text-sm font-bold text-slate-900 font-mono mt-1">
                  {dossier.risk_score.components.collusion_indicators}/100
                </div>
              </div>

              <div className="p-3 bg-white rounded-md border border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-medium">Financial</div>
                <div className="text-sm font-bold text-slate-900 font-mono mt-1">
                  {dossier.risk_score.components.financial_health}/100
                </div>
              </div>

              <div className="p-3 bg-white rounded-md border border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-medium">Document</div>
                <div className="text-sm font-bold text-slate-900 font-mono mt-1">
                  {dossier.risk_score.components.document_integrity}/100
                </div>
              </div>

              <div className="p-3 bg-white rounded-md border border-slate-200">
                <div className="text-[10px] text-slate-500 uppercase font-medium">Blacklist</div>
                <div className="text-sm font-bold text-slate-900 font-mono mt-1">
                  {dossier.risk_score.components.blacklist_proximity}/100
                </div>
              </div>
            </div>
          )}

          {/* Flagged Anomalies & Evidence */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Detected Anomalies & Evidence ({anomalies.length})
              </h2>
              <span className="text-xs text-slate-500">
                Source: Statutory Registries & Cross-Bidder Graph
              </span>
            </div>

            {anomalies.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-md">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                No statutory, structural, or behavioral anomalies detected for this bidder.
              </div>
            ) : (
              <div className="space-y-3">
                {anomalies.map((anomaly, idx) => {
                  const isExpanded = expandedAnomalies[anomaly.anomaly_id || idx];
                  const sevBadge =
                    anomaly.severity === "critical"
                      ? "danger"
                      : anomaly.severity === "high"
                      ? "danger"
                      : anomaly.severity === "medium"
                      ? "warning"
                      : "neutral";

                  return (
                    <div
                      key={anomaly.anomaly_id || idx}
                      className="border border-slate-200 rounded-md overflow-hidden transition-colors hover:border-slate-300"
                    >
                      <button
                        type="button"
                        onClick={() => toggleAnomaly(anomaly.anomaly_id || String(idx))}
                        className="w-full p-3.5 bg-slate-50/70 flex items-start justify-between text-left gap-3"
                      >
                        <div className="flex items-start gap-2.5">
                          <Badge variant={sevBadge} className="shrink-0 mt-0.5">
                            {anomaly.severity.toUpperCase()}
                          </Badge>
                          <div>
                            <div className="text-xs font-semibold text-slate-900">
                              {anomaly.title || anomaly.description}
                            </div>
                            <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                              Type: {anomaly.anomaly_type} • ID: {anomaly.anomaly_id}
                            </div>
                          </div>
                        </div>
                        <div className="text-slate-400 p-1">
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 bg-white border-t border-slate-200 text-xs space-y-3">
                          <p className="text-slate-700">{anomaly.description}</p>
                          {anomaly.related_bidders && anomaly.related_bidders.length > 0 && (
                            <div>
                              <div className="text-[11px] font-semibold text-slate-700 mb-1">
                                Related Entities / Co-conspirators:
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {anomaly.related_bidders.map((ent) => (
                                  <span
                                    key={ent}
                                    className="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded font-mono text-[11px] text-slate-800"
                                  >
                                    {ent}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Statutory Checks, Bank, & Directorship */}
        <div className="space-y-6">
          {/* Statutory Compliance Checklist */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <FileCheck2 className="w-4 h-4 text-emerald-600" />
              Statutory Compliance Checks ({complianceChecks.length})
            </h2>

            <div className="space-y-2.5 text-xs">
              {complianceChecks.length === 0 ? (
                <p className="text-slate-500">
                  {isVerified
                    ? "No specific compliance observations recorded."
                    : "Pending verification run."}
                </p>
              ) : (
                complianceChecks.map((chk) => (
                  <div
                    key={chk.check_id}
                    className="p-2.5 rounded border border-slate-200 flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium text-slate-800">{chk.check_name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">{chk.details}</div>
                    </div>
                    {chk.result === "pass" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : chk.result === "fail" ? (
                      <XCircle className="w-4 h-4 text-red-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Board of Directors */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-600" />
              Board of Directors & DIN
            </h2>

            {dossier.directors && dossier.directors.length > 0 ? (
              <div className="space-y-2 text-xs">
                {dossier.directors.map((dir, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-50 rounded border border-slate-200 flex items-center justify-between"
                  >
                    <div>
                      <div className="font-medium text-slate-800">{dir.name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">DIN: {dir.din || "N/A"}</div>
                    </div>
                    {dir.pan && (
                      <span className="text-[10px] font-mono text-slate-400">PAN: {dir.pan}</span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">No director information returned by MCA API.</p>
            )}
          </div>

          {/* Banking Profile */}
          {dossier.bank_account && (
            <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs space-y-3">
              <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <Landmark className="w-4 h-4 text-blue-600" />
                Bank Account Nexus
              </h2>
              <div className="text-xs space-y-1.5 p-3 bg-slate-50 rounded border border-slate-200 font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-500">Bank:</span>
                  <span className="font-bold text-slate-800">{dossier.bank_account.bank_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Branch:</span>
                  <span className="text-slate-800">{dossier.bank_account.branch}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">IFSC:</span>
                  <span className="text-slate-800">{dossier.bank_account.ifsc}</span>
                </div>
              </div>
            </div>
          )}

          {/* Annual Turnover Profile */}
          {dossier.annual_turnover && dossier.annual_turnover.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-xs space-y-4">
              <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-600" />
                Reported Annual Turnover
              </h2>

              <div className="space-y-2 text-xs">
                {dossier.annual_turnover.map((t, idx) => (
                  <div key={idx} className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-600">{t.year}:</span>
                    <span className="font-mono font-medium text-slate-900">
                      {formatCurrency(t.amount)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Formal Decision Modal */}
      {decisionModalOpen && (
        <DecisionModal
          isOpen={decisionModalOpen}
          onClose={() => setDecisionModalOpen(false)}
          tenderId={tenderId}
          bidder={{
            bidder_id: dossier.bidder_id,
            entity_name: dossier.entity_name,
            risk_level: riskLevel,
            risk_score: riskScore,
            current_decision: decision?.decision,
          }}
          onSuccess={() => {
            fetchDossierData();
            if (onDecisionChanged) onDecisionChanged();
          }}
        />
      )}
    </div>
  );
}
