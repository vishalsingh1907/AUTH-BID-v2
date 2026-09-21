"use client";

import React from "react";
import {
  FileText,
  Activity,
  Users,
  Network,
  Lock,
  FileCheck,
  Building2,
} from "lucide-react";
import { formatCurrency } from "../../lib/formatters";
import type { Tender } from "../../lib/types";

export type WorkspaceView =
  | "intake"
  | "pipeline"
  | "triage"
  | "dossier"
  | "graph"
  | "audit"
  | "report";

interface SidebarProps {
  currentView: WorkspaceView;
  onSelectView: (view: WorkspaceView) => void;
  tender: Tender | null;
  flaggedCount?: number;
  ringCount?: number;
}

interface NavItem {
  id: WorkspaceView;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  badge?: string | number;
  badgeVariant?: "danger" | "neutral";
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  tender,
  flaggedCount = 0,
  ringCount = 0,
}) => {
  const navItems: NavItem[] = [
    {
      id: "intake",
      label: "Tender Intake",
      icon: Building2,
    },
    {
      id: "pipeline",
      label: "Verification Pipeline",
      icon: Activity,
    },
    {
      id: "triage",
      label: "Triage Queue",
      icon: Users,
      badge: flaggedCount > 0 ? `${flaggedCount} Flagged` : undefined,
      badgeVariant: "danger",
    },
    {
      id: "dossier",
      label: "Bidder Dossier",
      icon: FileText,
    },
    {
      id: "graph",
      label: "Collusion OSINT Graph",
      icon: Network,
      badge: ringCount > 0 ? `${ringCount} Rings` : undefined,
      badgeVariant: "danger",
    },
    {
      id: "audit",
      label: "Tamper-Evident Chain",
      icon: Lock,
    },
    {
      id: "report",
      label: "Scrutiny Memo",
      icon: FileCheck,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200/90 flex flex-col justify-between flex-shrink-0 z-20 select-none">
      <div>
        {/* Brand Header */}
        <div
          onClick={() => onSelectView("intake")}
          className="p-4 border-b border-slate-100 flex items-center gap-3 cursor-pointer hover:bg-slate-50/70 transition"
          title="Return to Tender Intake"
        >
          <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center p-1 shadow-xs flex-shrink-0">
            <img
              src="/assets/logo-icon-inverted.png"
              alt="AuthBid Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h1 className="text-sm font-bold tracking-tight text-slate-900 leading-none">
                AuthBid
              </h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">
                GeM
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 font-medium">
              Procurement Intelligence
            </p>
          </div>
        </div>

        {/* Workflow Navigation */}
        <div className="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Investigation Workflow
        </div>
        <nav className="p-2 space-y-0.5">
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            const IconComp = item.icon;

            return (
              <button
                key={item.id}
                onClick={() => onSelectView(item.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition text-left cursor-pointer ${
                  isActive
                    ? "bg-slate-100 text-slate-900 font-semibold shadow-2xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50/80"
                }`}
              >
                <IconComp
                  size={16}
                  className={isActive ? "text-blue-600" : "text-slate-400"}
                />
                <span className="flex-1 truncate">{item.label}</span>
                {item.badge && (
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                      item.badgeVariant === "danger"
                        ? "bg-rose-50 text-rose-700 border border-rose-200/70"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Active Tender Card */}
      {tender && (
        <div className="p-3 border-t border-slate-100 bg-slate-50/50">
          <div className="bg-white p-3 rounded-lg border border-slate-200/70 shadow-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Active Tender
              </span>
              <span className="text-[11px] font-mono font-semibold text-slate-800">
                {formatCurrency(tender.estimated_value)}
              </span>
            </div>
            <p className="text-xs font-medium text-slate-900 line-clamp-2 mt-0.5 mb-1">
              {tender.title}
            </p>
            <p className="text-[10px] font-mono text-slate-400 truncate">
              {tender.tender_id}
            </p>
            <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <span>Authority:</span>
              <span className="font-medium text-slate-700 truncate max-w-[120px]">
                {tender.department || "NIC / MeitY"}
              </span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;
