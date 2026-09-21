"use client";

import React from "react";
import { Header } from "./Header";
import { Sidebar, type WorkspaceView } from "./Sidebar";
import type { Tender } from "../../lib/types";

interface AppShellProps {
  currentView: WorkspaceView;
  onSelectView: (view: WorkspaceView) => void;
  viewTitle: string;
  tender: Tender | null;
  flaggedCount?: number;
  ringCount?: number;
  onOpenCopilot: () => void;
  onOpenCompare?: () => void;
  compareCount?: number;
  onDemoReset: () => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentView,
  onSelectView,
  viewTitle,
  tender,
  flaggedCount = 0,
  ringCount = 0,
  onOpenCopilot,
  onOpenCompare,
  compareCount = 0,
  onDemoReset,
  children,
}) => {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-800 antialiased font-sans">
      {/* Sidebar Workflow Navigation */}
      <Sidebar
        currentView={currentView}
        onSelectView={onSelectView}
        tender={tender}
        flaggedCount={flaggedCount}
        ringCount={ringCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <Header
          currentViewTitle={viewTitle}
          onOpenCopilot={onOpenCopilot}
          onOpenCompare={onOpenCompare}
          compareCount={compareCount}
          onDemoReset={onDemoReset}
        />

        {/* Workspace Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-50/60">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppShell;
