"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { AppShell } from "./components/app-shell/AppShell";
import { WorkspaceView } from "./components/app-shell/Sidebar";
import PipelineRunner from "./components/pipeline/PipelineRunner";
import { TriageFilterBar } from "./components/triage/TriageFilterBar";
import { TriageQueue } from "./components/triage/TriageQueue";
import DossierView from "./components/dossier/DossierView";
import CollusionGraph from "./components/graph/CollusionGraph";
import AuditTrailView from "./components/audit/AuditTrailView";
import ScrutinyReportView from "./components/report/ScrutinyReportView";
import CommercialPriceAnalysis from "./components/CommercialPriceAnalysis";

import ShowCauseModal from "./components/ShowCauseModal";
import BidderCompareModal from "./components/BidderCompareModal";
import DocumentVault from "./components/DocumentVault";
import CopilotDrawer from "./components/CopilotDrawer";
import DecisionModal from "./components/modals/DecisionModal";

import { api } from "./lib/api";
import {
  Tender,
  BidderSummary,
  VerificationResult,
  OfficerDecision,
} from "./lib/types";

export default function WorkspacePage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>("GEM/2026/B/4521897");
  const [currentView, setCurrentView] = useState<WorkspaceView>("triage");
  const [selectedBidderId, setSelectedBidderId] = useState<string | null>(null);

  // Data states
  const [tender, setTender] = useState<Tender | null>(null);
  const [bidders, setBidders] = useState<BidderSummary[]>([]);
  const [results, setResults] = useState<VerificationResult[]>([]);
  const [decisions, setDecisions] = useState<Record<string, OfficerDecision>>({});
  const [loading, setLoading] = useState(true);

  // Pipeline simulation / run state
  const [isVerifying, setIsVerifying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [activeStageIndex, setActiveStageIndex] = useState(0);

  // Modal states
  const [showCauseBidderId, setShowCauseBidderId] = useState<string | null>(null);
  const [decisionBidderId, setDecisionBidderId] = useState<string | null>(null);
  const [documentVaultBidderId, setDocumentVaultBidderId] = useState<string | null>(null);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [selectedCompareIds, setSelectedCompareIds] = useState<string[]>([]);
  const [copilotOpen, setCopilotOpen] = useState(false);

  // Triage filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"all" | "low" | "medium" | "high_critical">("all");
  const [decisionFilter, setDecisionFilter] = useState<"all" | "pending" | "eligible" | "review" | "disqualified">("all");

  // Load tenders list
  useEffect(() => {
    api
      .getTenders()
      .then((tenderList) => {
        if (tenderList && tenderList.length > 0) {
          setTenders(tenderList);
          if (!selectedTenderId || !tenderList.some((t) => t.tender_id === selectedTenderId)) {
            setSelectedTenderId(tenderList[0].tender_id);
          }
        }
      })
      .catch((err) => {
        console.error("Failed to fetch tenders:", err);
      });
  }, []);

  // Load tender data, bidders, verification results, and officer decisions
  const loadWorkspaceData = useCallback(async () => {
    if (!selectedTenderId) return;
    setLoading(true);
    try {
      const [tenderData, biddersList, resultsResponse, decisionsList] = await Promise.all([
        api.getTender(selectedTenderId).catch(() => null),
        api.getBidders().catch(() => []),
        api.getResults(selectedTenderId).catch(() => null),
        api.getDecisions(selectedTenderId).catch(() => []),
      ]);

      if (tenderData) setTender(tenderData);
      if (biddersList) setBidders(biddersList);
      if (resultsResponse?.results) setResults(resultsResponse.results);

      // Convert decisions array to map
      const decisionMap: Record<string, OfficerDecision> = {};
      if (decisionsList && Array.isArray(decisionsList)) {
        decisionsList.forEach((d) => {
          decisionMap[d.bidder_id] = d;
        });
      }
      setDecisions(decisionMap);
    } catch (err) {
      console.error("Error loading workspace data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedTenderId]);

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  // Demo Reset Handler
  const handleDemoReset = async () => {
    try {
      await api.resetDemoData();
      await loadWorkspaceData();
      setSelectedBidderId(null);
      setSelectedCompareIds([]);
    } catch (err) {
      console.error("Failed to reset demo data:", err);
    }
  };

  // Run Verification Pipeline
  const handleRunVerification = async () => {
    setIsVerifying(true);
    setProgress(10);
    setActiveStageIndex(0);

    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 90) {
          clearInterval(interval);
          return 90;
        }
        const next = p + 15;
        setActiveStageIndex(Math.min(Math.floor(next / 12), 7));
        return next;
      });
    }, 400);

    try {
      await api.runVerification(selectedTenderId);
      setProgress(100);
      setActiveStageIndex(7);
      await loadWorkspaceData();
    } catch (err) {
      console.error("Verification run failed:", err);
    } finally {
      clearInterval(interval);
      setTimeout(() => {
        setIsVerifying(false);
        setProgress(0);
      }, 800);
    }
  };

  // Toggle compare selection
  const handleToggleCompareId = (bidderId: string) => {
    setSelectedCompareIds((prev) =>
      prev.includes(bidderId) ? prev.filter((id) => id !== bidderId) : [...prev, bidderId]
    );
  };

  // Filtered results for Triage Queue
  const filteredResults = useMemo(() => {
    return results.filter((r) => {
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = r.entity_name?.toLowerCase().includes(q);
        const matchesId = r.bidder_id?.toLowerCase().includes(q);
        if (!matchesName && !matchesId) return false;
      }

      // Risk filter
      const score = r.risk_score?.overall_score ?? 0;
      if (riskFilter === "low" && score >= 40) return false;
      if (riskFilter === "medium" && (score < 40 || score >= 70)) return false;
      if (riskFilter === "high_critical" && score < 70) return false;

      // Decision filter
      const dec = decisions[r.bidder_id]?.decision || "pending";
      if (decisionFilter !== "all" && dec !== decisionFilter) return false;

      return true;
    });
  }, [results, searchQuery, riskFilter, decisionFilter, decisions]);

  // Counts for triage filter bar
  const lowCount = results.filter((r) => (r.risk_score?.overall_score ?? 0) < 40).length;
  const mediumCount = results.filter((r) => {
    const s = r.risk_score?.overall_score ?? 0;
    return s >= 40 && s < 70;
  }).length;
  const highCriticalCount = results.filter((r) => (r.risk_score?.overall_score ?? 0) >= 70).length;

  const viewTitles: Record<WorkspaceView, string> = {
    intake: "Tender Intake & Eligibility Criteria",
    pipeline: "Verification Pipeline & Automated Scrutiny",
    triage: "Triage & Risk Review Queue",
    dossier: "Bidder Investigation Dossier",
    graph: "Collusion & Relationship Graph",
    audit: "Immutable Audit Trail & Cryptographic Ledger",
    report: "Defensible Scrutiny Report",
  };

  const activeTender = tender || {
    tender_id: selectedTenderId,
    title: "Procurement of Enterprise Cloud Infrastructure & Security Services",
    category: "Cloud Infrastructure",
    estimated_value: 485000000,
    currency: "INR",
    published_date: "2026-02-15T09:00:00Z",
    closing_date: "2026-03-31T17:00:00Z",
    ministry: "Ministry of Electronics and Information Technology (MeitY)",
    department: "National e-Governance Division",
    total_bidders: bidders.length || 12,
    flagged_bidders: highCriticalCount,
  };

  const selectedBidderForDecision = useMemo(() => {
    if (!decisionBidderId) return null;
    const res = results.find((r) => r.bidder_id === decisionBidderId);
    const summary = bidders.find((b) => b.bidder_id === decisionBidderId);
    return {
      bidder_id: decisionBidderId,
      entity_name: res?.entity_name || summary?.entity_name || decisionBidderId,
      risk_level: res?.risk_score?.risk_level,
      risk_score: res?.risk_score?.overall_score,
      current_decision: decisions[decisionBidderId]?.decision,
    };
  }, [decisionBidderId, results, bidders, decisions]);

  return (
    <AppShell
      currentView={currentView}
      onSelectView={(view: WorkspaceView) => {
        setCurrentView(view);
        if (view === "dossier" && !selectedBidderId) {
          setSelectedBidderId(bidders[0]?.bidder_id || "B001");
        }
      }}
      viewTitle={viewTitles[currentView]}
      tender={activeTender}
      flaggedCount={highCriticalCount}
      ringCount={2}
      onOpenCopilot={() => setCopilotOpen(true)}
      onOpenCompare={() => {
        if (selectedCompareIds.length === 0 && bidders.length >= 2) {
          setSelectedCompareIds([bidders[0].bidder_id, bidders[1].bidder_id]);
        }
        setCompareModalOpen(true);
      }}
      compareCount={selectedCompareIds.length}
      onDemoReset={handleDemoReset}
    >
      <div className="space-y-6">
        {/* VIEW: INTAKE */}
        {currentView === "intake" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
                <div>
                  <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    {activeTender.tender_id}
                  </span>
                  <h1 className="text-lg font-bold text-slate-900 mt-2">{activeTender.title}</h1>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {activeTender.ministry} • {activeTender.department}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentView("pipeline")}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors self-start sm:self-auto"
                >
                  Proceed to Pipeline →
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 block">Estimated Value</span>
                  <span className="font-bold text-slate-900 font-mono">₹48.50 Cr</span>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 block">Category</span>
                  <span className="font-bold text-slate-900">{activeTender.category}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 block">Total Bidders</span>
                  <span className="font-bold text-slate-900 font-mono">{bidders.length}</span>
                </div>
                <div className="p-3 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-500 block">Submission Closing</span>
                  <span className="font-bold text-slate-900 font-mono">{activeTender.closing_date.slice(0, 10)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW: PIPELINE */}
        {currentView === "pipeline" && (
          <PipelineRunner
            tender={activeTender}
            isVerifying={isVerifying}
            progress={progress}
            activeStageIndex={activeStageIndex}
            onRunVerification={handleRunVerification}
            onNavigateToTriage={() => setCurrentView("triage")}
            totalBiddersVerified={results.length}
          />
        )}

        {/* VIEW: TRIAGE */}
        {currentView === "triage" && (
          <div className="space-y-6">
            <TriageFilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              riskFilter={riskFilter}
              onRiskFilterChange={setRiskFilter}
              decisionFilter={decisionFilter}
              onDecisionFilterChange={setDecisionFilter}
              totalCount={results.length}
              lowCount={lowCount}
              mediumCount={mediumCount}
              highCriticalCount={highCriticalCount}
              selectedCompareCount={selectedCompareIds.length}
              onOpenCompare={() => {
                if (selectedCompareIds.length === 0 && bidders.length >= 2) {
                  setSelectedCompareIds([bidders[0].bidder_id, bidders[1].bidder_id]);
                }
                setCompareModalOpen(true);
              }}
            />

            <TriageQueue
              results={filteredResults}
              bidders={bidders}
              decisions={decisions}
              selectedCompareIds={selectedCompareIds}
              onToggleCompareId={handleToggleCompareId}
              onSelectBidderForDossier={(res) => {
                setSelectedBidderId(res.bidder_id);
                setCurrentView("dossier");
              }}
              onOpenDecisionModal={(bidderId) => setDecisionBidderId(bidderId)}
            />

            {/* Commercial Price Analysis Chart & Matrix */}
            <div className="pt-2">
              <CommercialPriceAnalysis
                bidders={bidders}
                results={results}
                onSelectBidder={(bidderId) => {
                  setSelectedBidderId(bidderId);
                  setCurrentView("dossier");
                }}
              />
            </div>
          </div>
        )}

        {/* VIEW: DOSSIER */}
        {currentView === "dossier" && (
          <div className="space-y-4">
            {/* Bidder Quick Switcher Bar */}
            <div className="bg-white border border-slate-200/90 rounded-xl p-3 shadow-2xs flex items-center gap-2 overflow-x-auto">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider pl-1 flex-shrink-0">
                Select Bidder:
              </span>
              <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
                {bidders.map((b) => {
                  const res = results.find((r) => r.bidder_id === b.bidder_id);
                  const isSelected = (selectedBidderId || bidders[0]?.bidder_id || "B001") === b.bidder_id;
                  const riskLevel = res?.risk_score?.risk_level || "low";
                  const badgeColor =
                    riskLevel === "critical"
                      ? "bg-rose-100 text-rose-800 border-rose-200"
                      : riskLevel === "high"
                      ? "bg-amber-100 text-amber-800 border-amber-200"
                      : riskLevel === "medium"
                      ? "bg-yellow-100 text-yellow-800 border-yellow-200"
                      : "bg-emerald-100 text-emerald-800 border-emerald-200";

                  return (
                    <button
                      key={b.bidder_id}
                      type="button"
                      onClick={() => setSelectedBidderId(b.bidder_id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all flex-shrink-0 cursor-pointer ${
                        isSelected
                          ? "bg-blue-50 border-blue-500 text-blue-900 shadow-2xs ring-1 ring-blue-500/20"
                          : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      <span className="font-mono font-bold">{b.bidder_id}</span>
                      <span className="truncate max-w-[130px]">{b.entity_name}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${badgeColor}`}>
                        {res ? `${res.risk_score?.overall_score ?? 0}` : "—"}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <DossierView
              bidderId={selectedBidderId || bidders[0]?.bidder_id || "B001"}
              tenderId={selectedTenderId}
              onBack={() => setCurrentView("triage")}
              onOpenShowCause={(id) => setShowCauseBidderId(id)}
              onOpenCompare={(id) => {
                if (!selectedCompareIds.includes(id)) {
                  setSelectedCompareIds((prev) => {
                    const updated = [...prev, id];
                    return updated.slice(-4);
                  });
                }
                setCompareModalOpen(true);
              }}
              onOpenDocumentVault={(id) => setDocumentVaultBidderId(id)}
              onTriggerVerification={handleRunVerification}
              onDecisionChanged={loadWorkspaceData}
            />
          </div>
        )}

        {/* VIEW: GRAPH */}
        {currentView === "graph" && (
          <CollusionGraph
            tenderId={selectedTenderId}
            onSelectBidder={(bidderId) => {
              setSelectedBidderId(bidderId);
              setCurrentView("dossier");
            }}
          />
        )}

        {/* VIEW: AUDIT */}
        {currentView === "audit" && (
          <AuditTrailView tenderId={selectedTenderId} />
        )}

        {/* VIEW: REPORT */}
        {currentView === "report" && (
          <ScrutinyReportView tenderId={selectedTenderId} />
        )}
      </div>

      {/* Decision Modal */}
      {decisionBidderId && selectedBidderForDecision && (
        <DecisionModal
          isOpen={Boolean(decisionBidderId)}
          onClose={() => setDecisionBidderId(null)}
          tenderId={selectedTenderId}
          bidder={selectedBidderForDecision}
          onSuccess={loadWorkspaceData}
        />
      )}

      {/* Show-Cause Notice Modal */}
      {showCauseBidderId && (
        <ShowCauseModal
          isOpen={Boolean(showCauseBidderId)}
          onClose={() => setShowCauseBidderId(null)}
          bidderId={showCauseBidderId}
        />
      )}

      {/* Multi-Bidder Comparison Modal */}
      {compareModalOpen && (
        <BidderCompareModal
          isOpen={compareModalOpen}
          onClose={() => setCompareModalOpen(false)}
          selectedIds={selectedCompareIds}
          onToggleSelectId={handleToggleCompareId}
          allBidders={bidders}
          allResults={results}
          decisions={decisions}
          onViewDossier={(bidderId: string) => {
            setCompareModalOpen(false);
            setSelectedBidderId(bidderId);
            setCurrentView("dossier");
          }}
        />
      )}

      {/* Document Vault Modal Dialog */}
      {documentVaultBidderId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <h3 className="text-sm font-bold text-slate-800">
                Document Vault • Bidder {documentVaultBidderId}
              </h3>
              <button
                type="button"
                onClick={() => setDocumentVaultBidderId(null)}
                className="text-slate-400 hover:text-slate-600 text-xs px-2 py-1 rounded"
              >
                ✕ Close
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <DocumentVault bidderId={documentVaultBidderId} />
            </div>
          </div>
        </div>
      )}

      {/* AI Procurement Copilot Drawer */}
      <CopilotDrawer
        isOpen={copilotOpen}
        onOpen={() => setCopilotOpen(true)}
        onClose={() => setCopilotOpen(false)}
        tenderId={selectedTenderId}
        selectedBidderId={selectedBidderId || undefined}
      />
    </AppShell>
  );
}
