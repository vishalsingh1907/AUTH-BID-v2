"use client";

import React from "react";
import {
  Play,
  RefreshCw,
  Clock,
  Building,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Users,
  ChevronRight,
} from "lucide-react";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { formatCurrency, formatDate } from "../../lib/formatters";
import type { Tender } from "../../lib/types";

interface TenderHeaderProps {
  tender: Tender;
  verificationStatus: "pending" | "in_progress" | "completed" | "failed";
  onTriggerVerification: () => void;
  onNavigateToTriage: () => void;
  onNavigateToPipeline: () => void;
  isVerifying: boolean;
  flaggedCount?: number;
  lastVerifiedAt?: string;
}

export const TenderHeader: React.FC<TenderHeaderProps> = ({
  tender,
  verificationStatus,
  onTriggerVerification,
  onNavigateToTriage,
  onNavigateToPipeline,
  isVerifying,
  flaggedCount = 0,
  lastVerifiedAt,
}) => {
  // Primary CTA determination based on status
  let primaryButton = null;
  if (isVerifying || verificationStatus === "in_progress") {
    primaryButton = (
      <Button
        variant="primary"
        size="md"
        onClick={onNavigateToPipeline}
        isLoading={isVerifying}
        rightIcon={<ChevronRight size={14} />}
      >
        View Live Pipeline
      </Button>
    );
  } else if (verificationStatus === "completed") {
    primaryButton = (
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="md"
          onClick={onNavigateToTriage}
          rightIcon={<ChevronRight size={14} />}
        >
          Review Flagged Bidders ({flaggedCount})
        </Button>
        <Button
          variant="outline"
          size="md"
          onClick={onTriggerVerification}
          leftIcon={<RefreshCw size={13} className="text-slate-500" />}
          title="Re-run verification across all registries"
        >
          Refresh Verification
        </Button>
      </div>
    );
  } else if (verificationStatus === "failed") {
    primaryButton = (
      <Button
        variant="danger"
        size="md"
        onClick={onTriggerVerification}
        leftIcon={<RefreshCw size={14} />}
      >
        Retry Verification
      </Button>
    );
  } else {
    primaryButton = (
      <Button
        variant="primary"
        size="md"
        onClick={onTriggerVerification}
        leftIcon={<Play size={14} />}
      >
        Start Verification
      </Button>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
      {/* Top Identity & Action Row */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap mb-1.5">
            <span className="font-mono text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              {tender.tender_id}
            </span>
            <Badge variant="info" size="sm">
              {tender.category}
            </Badge>
            {verificationStatus === "completed" && (
              <Badge variant={flaggedCount > 0 ? "danger" : "success"} size="sm" dot>
                {flaggedCount > 0 ? `${flaggedCount} Bidders Flagged` : "All Bidders Compliant"}
              </Badge>
            )}
            {verificationStatus === "in_progress" && (
              <Badge variant="warning" size="sm" dot>
                Verification Running
              </Badge>
            )}
            {verificationStatus === "pending" && (
              <Badge variant="neutral" size="sm" dot>
                Awaiting Verification
              </Badge>
            )}
          </div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            {tender.title}
          </h2>
        </div>

        {/* Action Button */}
        <div className="flex-shrink-0">{primaryButton}</div>
      </div>

      {/* Metadata Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t border-slate-100 text-xs">
        <div>
          <span className="text-slate-400 font-medium flex items-center gap-1.5 mb-0.5">
            <Building size={13} />
            <span>Procuring Authority</span>
          </span>
          <p className="font-semibold text-slate-800 truncate">
            {tender.department || "NIC"} • {tender.ministry || "MeitY"}
          </p>
        </div>

        <div>
          <span className="text-slate-400 font-medium flex items-center gap-1.5 mb-0.5">
            <Calendar size={13} />
            <span>Submission Window</span>
          </span>
          <p className="font-semibold text-slate-800">
            {formatDate(tender.published_date)} – {formatDate(tender.closing_date)}
          </p>
        </div>

        <div>
          <span className="text-slate-400 font-medium flex items-center gap-1.5 mb-0.5">
            <Users size={13} />
            <span>Submitted Bids</span>
          </span>
          <p className="font-semibold text-slate-800 font-mono">
            {tender.bidder_count || 12} Bids (Est: {formatCurrency(tender.estimated_value)})
          </p>
        </div>

        <div>
          <span className="text-slate-400 font-medium flex items-center gap-1.5 mb-0.5">
            <Clock size={13} />
            <span>Evidence Freshness</span>
          </span>
          <p className="font-semibold text-slate-800">
            {lastVerifiedAt ? formatDate(lastVerifiedAt) : "Pending Pipeline Run"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default TenderHeader;
