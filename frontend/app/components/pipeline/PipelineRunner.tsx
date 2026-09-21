"use client";

import React from "react";
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Play,
  Sparkles,
  ShieldCheck,
  Network,
  Lock,
  FileSearch,
  Database,
  Building,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import type { Tender } from "../../lib/types";

interface PipelineRunnerProps {
  tender: Tender;
  isVerifying: boolean;
  progress: number;
  activeStageIndex: number;
  onRunVerification: () => void;
  onNavigateToTriage: () => void;
  completedAt?: string;
  totalBiddersVerified?: number;
}

interface PipelineStage {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const STAGES: PipelineStage[] = [
  {
    id: "intake",
    title: "1. Tender & RFP Clause Extraction",
    description: "Ingesting tender specifications, eligibility criteria, and bidder bid submissions.",
    icon: Building,
  },
  {
    id: "registries",
    title: "2. Statutory Registry Cross-Verification",
    description: "Querying live MCA21 (DIN), GSTN (GSTR-3B), CBDT (PAN), and MSME Udyam portals.",
    icon: Database,
  },
  {
    id: "financials",
    title: "3. Financial Health & Filing Consistency",
    description: "Auditing annual turnovers, 3-year balance sheets, and filing gap heuristics.",
    icon: FileSearch,
  },
  {
    id: "documents",
    title: "4. Document Integrity & OCR Validation",
    description: "Matching OEM authorization letters, ISO certificates, and UDIN authenticity.",
    icon: ShieldCheck,
  },
  {
    id: "anomalies",
    title: "5. Cross-Bidder Anomaly Detection",
    description: "Scanning for shell company behavior, debarment proximity, and registration flaws.",
    icon: AlertCircle,
  },
  {
    id: "collusion",
    title: "6. Collusion & Entity Resolution Graph",
    description: "Constructing OSINT graph across shared directors, physical addresses, and bank accounts.",
    icon: Network,
  },
  {
    id: "scoring",
    title: "7. Composite Risk Scoring & Explanation",
    description: "Evaluating multi-factor weighted risk models and generating plain-language findings.",
    icon: Sparkles,
  },
  {
    id: "audit",
    title: "8. SHA-256 Audit Chain Anchoring",
    description: "Sealing all verification outputs into immutable cryptographic blocks with external anchor.",
    icon: Lock,
  },
];

export const PipelineRunner: React.FC<PipelineRunnerProps> = ({
  tender,
  isVerifying,
  progress,
  activeStageIndex,
  onRunVerification,
  onNavigateToTriage,
  completedAt,
  totalBiddersVerified = 0,
}) => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Pipeline Header */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Verification Engine
            </span>
            {isVerifying ? (
              <Badge variant="warning" size="sm" dot>
                Running Multi-Agent Pipeline ({progress}%)
              </Badge>
            ) : completedAt ? (
              <Badge variant="success" size="sm" dot>
                Pipeline Completed ({totalBiddersVerified} Bidders)
              </Badge>
            ) : (
              <Badge variant="neutral" size="sm" dot>
                Ready to Execute
              </Badge>
            )}
          </div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            Multi-Agent Statutory Compliance & Collusion Pipeline
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Autonomous multi-agent verification system executing cross-registry data pulls, OSINT entity resolution, and cryptographic audit hashing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {completedAt && !isVerifying && (
            <Button variant="outline" size="md" onClick={onNavigateToTriage}>
              Go to Triage Queue
            </Button>
          )}
          <Button
            variant="primary"
            size="md"
            onClick={onRunVerification}
            isLoading={isVerifying}
            leftIcon={!isVerifying && <Play size={14} />}
          >
            {isVerifying ? "Processing..." : completedAt ? "Re-Run Pipeline" : "Start Pipeline"}
          </Button>
        </div>
      </div>

      {/* Progress Bar (if running) */}
      {isVerifying && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-800 mb-2">
            <span>Overall Verification Progress</span>
            <span className="font-mono text-blue-600">{progress}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stages Timeline */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
          Pipeline Verification Stages
        </h3>

        <div className="divide-y divide-slate-100">
          {STAGES.map((stage, idx) => {
            const IconComp = stage.icon;
            const isStageCompleted = completedAt && !isVerifying ? true : idx < activeStageIndex;
            const isStageActive = isVerifying && idx === activeStageIndex;

            return (
              <div
                key={stage.id}
                className={`py-3.5 flex items-start gap-4 transition-colors ${
                  isStageActive ? "bg-blue-50/40 -mx-3 px-3 rounded-lg" : ""
                }`}
              >
                {/* Stage Icon Status */}
                <div className="mt-0.5 flex-shrink-0">
                  {isStageCompleted ? (
                    <div className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                      <CheckCircle2 size={15} />
                    </div>
                  ) : isStageActive ? (
                    <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center animate-pulse">
                      <Loader2 size={15} className="animate-spin" />
                    </div>
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center">
                      <Clock size={15} />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className={`text-xs font-bold ${isStageActive ? "text-blue-900" : isStageCompleted ? "text-slate-900" : "text-slate-600"}`}>
                      {stage.title}
                    </h4>
                    <span className="text-[10px] font-mono text-slate-400">
                      {isStageCompleted ? "Completed" : isStageActive ? "In Progress" : "Queued"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {stage.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default PipelineRunner;
