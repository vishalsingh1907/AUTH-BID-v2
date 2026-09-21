"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Lock,
  RotateCcw,
  AlertTriangle,
  FileCode,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Layers,
  Key,
  Calendar,
  UserCheck,
} from "lucide-react";
import { api } from "../../lib/api";
import { AuditTrailResponse, AuditEntry, AnchorReceipt } from "../../lib/types";
import { formatDateTime, truncateHash } from "../../lib/formatters";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface AuditTrailViewProps {
  tenderId: string;
}

export default function AuditTrailView({ tenderId }: AuditTrailViewProps) {
  const [data, setData] = useState<AuditTrailResponse | null>(null);
  const [anchor, setAnchor] = useState<AnchorReceipt | null>(null);
  const [loading, setLoading] = useState(true);
  const [tampering, setTampering] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [anchorOpen, setAnchorOpen] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [expandedEntries, setExpandedEntries] = useState<Record<string, boolean>>({});

  const fetchAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAuditTrail();
      if (res) {
        setData(res);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load audit trail.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnchor = async () => {
    try {
      const res = await api.getAnchorReceipt();
      if (res?.latest_anchor) {
        setAnchor(res.latest_anchor);
      }
    } catch (err) {
      console.error("Failed to load anchor receipt", err);
    }
  };

  useEffect(() => {
    fetchAudit();
    fetchAnchor();
  }, [tenderId]);

  const handleSimulateTamper = async () => {
    setTampering(true);
    setActionSuccess(null);
    try {
      await api.tamperAuditTrail();
      setActionSuccess("Tamper simulation executed. SHA-256 hash chain broken to prove mathematical audit verification.");
      await fetchAudit();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Tamper simulation failed.");
    } finally {
      setTampering(false);
    }
  };

  const handleRestoreChain = async () => {
    setRestoring(true);
    setActionSuccess(null);
    try {
      await api.restoreAuditTrail();
      setActionSuccess("Cryptographic hash chain restored to genuine state.");
      await fetchAudit();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Chain restoration failed.");
    } finally {
      setRestoring(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(id);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const toggleExpand = (stepId: string) => {
    setExpandedEntries((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-white rounded-lg border border-slate-200 text-slate-500 space-y-3">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-600">Verifying SHA-256 hash chain and RFC 3161 integrity...</p>
      </div>
    );
  }

  const isValid = data?.chain_integrity?.valid ?? true;
  const brokenBlock = data?.chain_integrity?.broken_block ?? null;
  const entries = data?.entries || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Lock className="w-4 h-4 text-blue-600" />
            Immutable Audit Trail & Cryptographic Ledger
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Every verification event, anomaly discovery, and officer decision is recorded in an immutable SHA-256 hash chain.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {anchor && (
            <Button variant="outline" size="sm" onClick={() => setAnchorOpen(!anchorOpen)}>
              <FileCode className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              {anchorOpen ? "Hide Anchor" : "RFC 3161 Anchor"}
            </Button>
          )}

          {isValid ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSimulateTamper}
              disabled={tampering}
              className="text-red-700 border-red-200 hover:bg-red-50"
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1.5 text-red-600" />
              {tampering ? "Simulating..." : "Simulate Tamper"}
            </Button>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={handleRestoreChain}
              disabled={restoring}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
              {restoring ? "Restoring..." : "Restore Chain"}
            </Button>
          )}
        </div>
      </div>

      {/* Chain Status Banner */}
      <div
        className={`p-4 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
          isValid
            ? "bg-emerald-50/60 border-emerald-200 text-emerald-950"
            : "bg-red-50/70 border-red-200 text-red-950"
        }`}
      >
        <div className="flex items-start gap-3">
          {isValid ? (
            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600 shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
          )}
          <div>
            <div className="text-sm font-bold flex items-center gap-2">
              <span>{isValid ? "Audit Chain Integrity: VERIFIED" : "Audit Chain Integrity: COMPROMISED"}</span>
              <Badge variant={isValid ? "success" : "danger"}>
                {isValid ? "100% Intact" : `Broken at Block: ${brokenBlock}`}
              </Badge>
            </div>
            <p className="text-xs text-slate-700 mt-1">
              {isValid
                ? `All ${entries.length} consecutive blocks satisfy SHA-256 recursive cryptographic chaining and timestamp consensus.`
                : `Tampering detected at Block ${brokenBlock}. Hash mismatch between prev_hash and current block payload hash.`}
            </p>
          </div>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end justify-between text-xs text-slate-600 shrink-0">
          <div>
            Total Blocks: <span className="font-mono font-bold text-slate-900">{entries.length}</span>
          </div>
          <div className="text-[11px] text-slate-500 font-mono">Tender: {tenderId}</div>
        </div>
      </div>

      {/* Notification Banner */}
      {actionSuccess && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-xs text-blue-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* RFC 3161 Anchor Drawer */}
      {anchorOpen && anchor && (
        <div className="p-5 bg-slate-900 text-slate-200 rounded-lg border border-slate-800 shadow-lg space-y-3 font-mono text-xs animate-in fade-in">
          <div className="flex items-center justify-between text-slate-400 pb-2 border-b border-slate-800 font-sans">
            <span className="font-semibold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-blue-400" />
              RFC 3161 Trusted Timestamp Authority (TSA) Receipt
            </span>
            <span className="text-[11px]">e-Procurement Anchor</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
            <div>
              <span className="text-slate-500 block">Root Hash (Merkle Root):</span>
              <span className="text-emerald-400 font-bold break-all">{anchor.root_hash || anchor.merkle_root}</span>
            </div>
            <div>
              <span className="text-slate-500 block">External TSA Service:</span>
              <span className="text-slate-200">{anchor.external_service}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Anchored At:</span>
              <span className="text-slate-200">{formatDateTime(anchor.anchored_at)}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Digital Signature (RSA-4096):</span>
              <span className="text-slate-400 break-all">{anchor.digital_signature?.slice(0, 48)}...</span>
            </div>
          </div>
        </div>
      )}

      {/* Ledger Block List */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            Cryptographic Block Sequence
          </h3>
          <span className="text-xs text-slate-500 font-mono">Algorithm: SHA-256 Recursive</span>
        </div>

        <div className="divide-y divide-slate-200">
          {entries.map((entry, idx) => {
            const isBrokenBlock = brokenBlock !== null && entry.step_id === brokenBlock;
            const isExpanded = expandedEntries[entry.step_id || String(idx)];

            return (
              <div
                key={entry.step_id || idx}
                className={`p-4 transition-colors ${
                  isBrokenBlock ? "bg-red-50/40" : "hover:bg-slate-50/70"
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-14 h-7 rounded flex items-center justify-center font-mono text-xs font-bold border ${
                        isBrokenBlock
                          ? "bg-red-100 border-red-300 text-red-800"
                          : "bg-slate-100 border-slate-300 text-slate-700"
                      }`}
                    >
                      {entry.step_id || `#${idx}`}
                    </span>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-slate-900 font-mono">
                          {entry.action}
                        </span>
                        {isBrokenBlock && <Badge variant="danger">Hash Mismatch</Badge>}
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono mt-0.5">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDateTime(entry.timestamp)}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <UserCheck className="w-3 h-3" />
                          Actor: {entry.agent_id}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Hash Badges */}
                  <div className="flex items-center gap-2">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 font-mono uppercase">Block Hash</div>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(entry.current_hash, `hash-${entry.step_id}`)}
                        className="text-xs font-mono text-slate-700 hover:text-blue-600 flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded border border-slate-200"
                      >
                        {truncateHash(entry.current_hash, 8)}
                        {copiedHash === `hash-${entry.step_id}` ? (
                          <Check className="w-3 h-3 text-emerald-600" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-400" />
                        )}
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleExpand(entry.step_id || String(idx))}
                      className="p-1.5 text-slate-400 hover:text-slate-600 rounded transition-colors"
                      aria-label="Toggle details"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expandable Payload */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-slate-200/60 text-xs space-y-2 font-mono">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 bg-slate-50 rounded border border-slate-200">
                        <span className="text-slate-500 block mb-0.5">Previous Hash:</span>
                        <span className="text-slate-700 break-all">{entry.prev_hash}</span>
                      </div>
                      <div className="p-2 bg-slate-50 rounded border border-slate-200">
                        <span className="text-slate-500 block mb-0.5">Block Current Hash:</span>
                        <span className="text-slate-700 break-all">{entry.current_hash}</span>
                      </div>
                    </div>

                    {entry.details && (
                      <div className="p-2.5 bg-slate-900 text-slate-200 rounded border border-slate-800 overflow-x-auto text-[11px]">
                        <span className="text-slate-400 block mb-1 font-sans font-semibold">
                          Recorded Block Payload:
                        </span>
                        <pre className="font-mono">{JSON.stringify(entry.details, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
