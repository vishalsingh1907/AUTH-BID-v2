"use client";

import React from "react";
import { Search, Scale } from "lucide-react";
import { Button } from "../ui/Button";

interface TriageFilterBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  riskFilter: "all" | "low" | "medium" | "high_critical";
  onRiskFilterChange: (f: "all" | "low" | "medium" | "high_critical") => void;
  decisionFilter: "all" | "pending" | "eligible" | "review" | "disqualified";
  onDecisionFilterChange: (d: "all" | "pending" | "eligible" | "review" | "disqualified") => void;
  totalCount: number;
  lowCount: number;
  mediumCount: number;
  highCriticalCount: number;
  selectedCompareCount: number;
  onOpenCompare?: () => void;
}

export const TriageFilterBar: React.FC<TriageFilterBarProps> = ({
  searchQuery,
  onSearchChange,
  riskFilter,
  onRiskFilterChange,
  decisionFilter,
  onDecisionFilterChange,
  totalCount,
  lowCount,
  mediumCount,
  highCriticalCount,
  selectedCompareCount,
  onOpenCompare,
}) => {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-xs">
      {/* Search & Compare */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search bidder name, ID, PAN..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:bg-white focus:border-slate-400 w-60 text-slate-900 transition"
          />
        </div>

        {onOpenCompare && (
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenCompare}
            leftIcon={<Scale size={13} className="text-slate-500" />}
          >
            Compare ({selectedCompareCount})
          </Button>
        )}
      </div>

      {/* Segmented Filter Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Risk Filter Segmented Control */}
        <div className="flex items-center p-0.5 bg-slate-100 rounded-lg border border-slate-200/80 text-xs font-medium">
          <button
            onClick={() => onRiskFilterChange("all")}
            className={`px-2.5 py-1 rounded-md transition ${
              riskFilter === "all" ? "bg-white text-slate-900 shadow-2xs font-semibold" : "text-slate-500 hover:text-slate-900"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => onRiskFilterChange("high_critical")}
            className={`px-2.5 py-1 rounded-md transition ${
              riskFilter === "high_critical" ? "bg-white text-rose-700 shadow-2xs font-semibold" : "text-slate-500 hover:text-rose-700"
            }`}
          >
            Critical ({highCriticalCount})
          </button>
          <button
            onClick={() => onRiskFilterChange("medium")}
            className={`px-2.5 py-1 rounded-md transition ${
              riskFilter === "medium" ? "bg-white text-amber-700 shadow-2xs font-semibold" : "text-slate-500 hover:text-amber-700"
            }`}
          >
            Medium ({mediumCount})
          </button>
          <button
            onClick={() => onRiskFilterChange("low")}
            className={`px-2.5 py-1 rounded-md transition ${
              riskFilter === "low" ? "bg-white text-emerald-700 shadow-2xs font-semibold" : "text-slate-500 hover:text-emerald-700"
            }`}
          >
            Clean ({lowCount})
          </button>
        </div>

        {/* Decision Filter Dropdown */}
        <select
          value={decisionFilter}
          onChange={(e) => onDecisionFilterChange(e.target.value as any)}
          className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-slate-400 font-medium"
        >
          <option value="all">All Decisions</option>
          <option value="pending">Pending Adjudication</option>
          <option value="eligible">Qualified for L1</option>
          <option value="review">Referred for Scrutiny</option>
          <option value="disqualified">Disqualified</option>
        </select>
      </div>
    </div>
  );
};

export default TriageFilterBar;
