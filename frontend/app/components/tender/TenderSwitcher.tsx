"use client";

import React, { useState } from "react";
import { ChevronDown, Check, Building2 } from "lucide-react";
import type { Tender } from "../../lib/types";

interface TenderSwitcherProps {
  tenders: Tender[];
  selectedTenderId: string;
  onSelectTender: (tenderId: string) => void;
}

export const TenderSwitcher: React.FC<TenderSwitcherProps> = ({
  tenders,
  selectedTenderId,
  onSelectTender,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const currentTender = tenders.find((t) => t.tender_id === selectedTenderId) || tenders[0];

  return (
    <div className="relative inline-block text-left select-none">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 transition cursor-pointer shadow-xs"
      >
        <Building2 size={13} className="text-blue-600" />
        <span className="font-mono text-[11px] text-slate-500">{currentTender?.tender_id}</span>
        <ChevronDown size={13} className="text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-1.5 w-72 bg-white border border-slate-200 rounded-xl shadow-lg z-50 py-1 overflow-hidden animate-fade-in">
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-100">
            Available Procurement Tenders
          </div>
          <div className="max-h-60 overflow-y-auto">
            {tenders.map((tender) => {
              const isSelected = tender.tender_id === selectedTenderId;
              return (
                <div
                  key={tender.tender_id}
                  onClick={() => {
                    onSelectTender(tender.tender_id);
                    setIsOpen(false);
                  }}
                  className={`px-3 py-2.5 flex items-start justify-between gap-2 hover:bg-slate-50 cursor-pointer transition ${
                    isSelected ? "bg-slate-50" : ""
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11px] font-bold text-slate-900">
                        {tender.tender_id}
                      </span>
                      {tender.verification_status === "completed" && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">
                          Verified
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-1 mt-0.5">
                      {tender.title}
                    </p>
                  </div>
                  {isSelected && <Check size={14} className="text-blue-600 mt-1 flex-shrink-0" />}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default TenderSwitcher;
