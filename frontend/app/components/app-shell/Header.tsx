"use client";

import React, { useState } from "react";
import { Sparkles, RefreshCw, Shield, UserCheck, Scale, CheckCircle2 } from "lucide-react";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { api, getActiveRole, setActiveRole } from "../../lib/api";

interface HeaderProps {
  currentViewTitle: string;
  onOpenCopilot: () => void;
  onOpenCompare?: () => void;
  compareCount?: number;
  onDemoReset: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentViewTitle,
  onOpenCopilot,
  onOpenCompare,
  compareCount = 0,
  onDemoReset,
}) => {
  const [role, setRole] = useState<string>(getActiveRole());
  const [isResetting, setIsResetting] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleRoleToggle = () => {
    const newRole = role === "officer" ? "admin" : "officer";
    setActiveRole(newRole);
    setRole(newRole);
  };

  const handleResetDemo = async () => {
    setIsResetting(true);
    try {
      await api.resetDemoData();
      setResetSuccess(true);
      setTimeout(() => setResetSuccess(false), 2500);
      onDemoReset();
    } catch (err) {
      console.error("Failed to reset demo data:", err);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <header className="h-14 bg-white border-b border-slate-200/90 px-6 flex items-center justify-between flex-shrink-0 z-10 select-none">
      {/* View Title & Breadcrumb */}
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-slate-900 tracking-tight">
          {currentViewTitle}
        </h1>

        {/* Freshness / Live Connectivity Badge */}
        <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-0.5 bg-slate-50 border border-slate-200/80 rounded-full text-[11px] font-medium text-slate-600">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>5 Statutory Registries Synced</span>
        </div>
      </div>

      {/* Header Actions */}
      <div className="flex items-center gap-2">
        {/* Compare Matrix Trigger (if compare available) */}
        {onOpenCompare && (
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenCompare}
            leftIcon={<Scale size={13} className="text-slate-500" />}
          >
            Compare ({compareCount})
          </Button>
        )}

        {/* AI Vigilance Copilot */}
        <Button
          variant="outline"
          size="sm"
          onClick={onOpenCopilot}
          leftIcon={<Sparkles size={13} className="text-blue-600" />}
        >
          AI Copilot
        </Button>

        {/* Role Switcher Pill */}
        <button
          onClick={handleRoleToggle}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-slate-100/80 hover:bg-slate-200/70 border border-slate-200 rounded-lg text-slate-700 transition cursor-pointer"
          title={`Active Role: ${role.toUpperCase()}. Click to switch between Officer and System Admin.`}
        >
          <UserCheck size={13} className={role === "admin" ? "text-amber-700" : "text-slate-500"} />
          <span className="capitalize text-[11px] font-semibold">{role}</span>
        </button>

        {/* Demo Scenario Reset Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleResetDemo}
          isLoading={isResetting}
          leftIcon={resetSuccess ? <CheckCircle2 size={13} className="text-emerald-600" /> : <RefreshCw size={12} className="text-slate-400" />}
          title="Reset in-memory demo scenario to starting state"
        >
          {resetSuccess ? "Reset Done" : "Reset Demo"}
        </Button>
      </div>
    </header>
  );
};

export default Header;
