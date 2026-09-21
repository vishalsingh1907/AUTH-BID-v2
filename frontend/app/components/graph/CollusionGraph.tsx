"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Network,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Filter,
  ShieldAlert,
  Info,
  ChevronRight,
  CheckCircle2,
  Layers,
  Eye,
  EyeOff,
} from "lucide-react";
import { api } from "../../lib/api";
import { GraphData, GraphNode, GraphEdge, CollusionCluster } from "../../lib/types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

interface CollusionGraphProps {
  tenderId: string;
  onSelectBidder?: (bidderId: string) => void;
}

interface NodePosition {
  x: number;
  y: number;
  radius: number;
}

export default function CollusionGraph({ tenderId, onSelectBidder }: CollusionGraphProps) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Investigation view states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState<string | "all">("all");
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);
  const [viewMode, setViewMode] = useState<"graph" | "table">("graph");

  // Transform states
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 520 });

  // Fetch graph data from backend
  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getCollusionGraph(tenderId);
      if (res && res.nodes && res.nodes.length > 0) {
        setData(res);
      } else {
        setData(res || null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load collusion graph from server.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [tenderId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Observe container dimensions for responsiveness
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        if (width > 300) {
          setCanvasSize({ width: Math.floor(width), height: 520 });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Filtered nodes and edges based on cluster and suspicious-only filter
  const { filteredNodes, filteredEdges } = useMemo(() => {
    if (!data) return { filteredNodes: [], filteredEdges: [] };

    let nodes = data.nodes;
    let edges = data.edges;

    // Filter by cluster
    if (selectedClusterId !== "all") {
      const cluster = data.clusters.find((c) => c.cluster_id === selectedClusterId);
      const memberIds = new Set(cluster?.members || []);

      // Keep cluster member bidders and edges connecting them
      const clusterEdges = edges.filter(
        (e) => memberIds.has(e.source) || memberIds.has(e.target)
      );
      const connectedNodeIds = new Set<string>();
      clusterEdges.forEach((e) => {
        connectedNodeIds.add(e.source);
        connectedNodeIds.add(e.target);
      });
      memberIds.forEach((m) => connectedNodeIds.add(m));

      nodes = nodes.filter((n) => connectedNodeIds.has(n.id));
      edges = clusterEdges;
    }

    // Filter suspicious only
    if (suspiciousOnly) {
      edges = edges.filter((e) => e.is_suspicious);
      const edgeNodeIds = new Set<string>();
      edges.forEach((e) => {
        edgeNodeIds.add(e.source);
        edgeNodeIds.add(e.target);
      });
      nodes = nodes.filter((n) => edgeNodeIds.has(n.id) || n.type === "bidder");
    }

    return { filteredNodes: nodes, filteredEdges: edges };
  }, [data, selectedClusterId, suspiciousOnly]);

  // Deterministic, stable position mapping (seeded layout, no Math.random)
  const nodePositions = useMemo(() => {
    const map = new Map<string, NodePosition>();
    if (!data) return map;

    const { width, height } = canvasSize;
    const centerX = width / 2;
    const centerY = height / 2;

    const bidders = data.nodes.filter((n) => n.type === "bidder");
    const secondaryNodes = data.nodes.filter((n) => n.type !== "bidder");

    // Layout bidders evenly on an outer ellipse
    const rx = Math.min(width, height) * 0.38;
    const ry = Math.min(width, height) * 0.35;

    bidders.forEach((bidder, idx) => {
      const angle = (idx / Math.max(bidders.length, 1)) * 2 * Math.PI - Math.PI / 2;
      map.set(bidder.id, {
        x: centerX + rx * Math.cos(angle),
        y: centerY + ry * Math.sin(angle),
        radius: 18,
      });
    });

    // Layout secondary evidence nodes deterministically
    secondaryNodes.forEach((node, idx) => {
      // Find connected bidders
      const connectedEdges = data.edges.filter((e) => e.source === node.id || e.target === node.id);
      const connectedBidders = connectedEdges.map((e) => (e.source === node.id ? e.target : e.source));

      let x = centerX;
      let y = centerY;

      if (connectedBidders.length > 0) {
        // Average coordinates of connected bidders with inward attraction
        let sumX = 0;
        let sumY = 0;
        let count = 0;
        connectedBidders.forEach((bidderId) => {
          const bPos = map.get(bidderId);
          if (bPos) {
            sumX += bPos.x;
            sumY += bPos.y;
            count++;
          }
        });

        if (count > 0) {
          const avgX = sumX / count;
          const avgY = sumY / count;
          // Pull 40% toward center
          x = avgX * 0.65 + centerX * 0.35;
          y = avgY * 0.65 + centerY * 0.35;
        }
      } else {
        // Fallback inner ring distribution
        const innerAngle = (idx / Math.max(secondaryNodes.length, 1)) * 2 * Math.PI;
        const innerR = Math.min(width, height) * 0.18;
        x = centerX + innerR * Math.cos(innerAngle);
        y = centerY + innerR * Math.sin(innerAngle);
      }

      map.set(node.id, { x, y, radius: 11 });
    });

    return map;
  }, [data, canvasSize]);

  // Canvas render loop
  useEffect(() => {
    if (viewMode !== "graph" || !canvasRef.current || !data) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasSize.width * dpr;
    canvas.height = canvasSize.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);
    ctx.save();

    // Pan & Zoom
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    const activeNodeIds = new Set(filteredNodes.map((n) => n.id));

    // 1. Draw Edges
    filteredEdges.forEach((edge) => {
      const sourcePos = nodePositions.get(edge.source);
      const targetPos = nodePositions.get(edge.target);
      if (!sourcePos || !targetPos) return;

      ctx.beginPath();
      ctx.moveTo(sourcePos.x, sourcePos.y);
      ctx.lineTo(targetPos.x, targetPos.y);

      if (edge.is_suspicious) {
        ctx.strokeStyle = "#dc2626"; // Crimson for collusion nexus
        ctx.lineWidth = 2.2;
        ctx.setLineDash([5, 4]);
      } else {
        ctx.strokeStyle = "#cbd5e1"; // Muted slate for neutral relations
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
      }

      ctx.stroke();
      ctx.setLineDash([]);

      // Render edge label if suspicious and either focused or zoomed
      if (edge.is_suspicious && edge.relationship && (selectedClusterId !== "all" || zoom >= 1.3)) {
        const midX = (sourcePos.x + targetPos.x) / 2;
        const midY = (sourcePos.y + targetPos.y) / 2;
        ctx.font = "9px Inter, sans-serif";
        ctx.fillStyle = "#991b1b";
        ctx.textAlign = "center";
        ctx.fillText(edge.relationship.replace(/_/g, " "), midX, midY - 4);
      }
    });

    // 2. Draw Nodes
    filteredNodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;

      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isBidder = node.type === "bidder";
      const radius = isBidder ? 18 : 11;

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);

      // Node colors based on risk and type
      if (isBidder) {
        const risk = node.risk_level?.toLowerCase();
        if (risk === "critical" || risk === "high") {
          ctx.fillStyle = "#fee2e2";
          ctx.strokeStyle = "#dc2626";
        } else if (risk === "medium") {
          ctx.fillStyle = "#fef3c7";
          ctx.strokeStyle = "#d97706";
        } else {
          ctx.fillStyle = "#ecfdf5";
          ctx.strokeStyle = "#059669";
        }
      } else {
        // Secondary indicator (director, address, bank, etc.)
        ctx.fillStyle = "#f8fafc";
        ctx.strokeStyle = "#64748b";
      }

      // Border styling
      ctx.lineWidth = isSelected ? 3.5 : isHovered ? 2.5 : 1.5;
      if (isSelected) {
        ctx.strokeStyle = "#0055ff"; // Active electric blue
      }
      ctx.fill();
      ctx.stroke();

      // Node icon/text indicator inside node
      ctx.font = isBidder ? "bold 10px Inter, sans-serif" : "9px Inter, sans-serif";
      ctx.fillStyle = isSelected ? "#0055ff" : "#1e293b";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(isBidder ? node.id : node.type.slice(0, 3).toUpperCase(), pos.x, pos.y);

      // 3. Level-of-Detail Label Rendering:
      // Show bidder labels always.
      // Show secondary labels ONLY when hovered, selected, filtered to cluster, or high zoom.
      const shouldShowLabel =
        isBidder ||
        isSelected ||
        isHovered ||
        selectedClusterId !== "all" ||
        zoom >= 1.4;

      if (shouldShowLabel) {
        const fullLabel = node.label || node.id;
        // Truncate label to keep view calm and prevent overlaps
        const truncatedLabel =
          isBidder && fullLabel.length > 20 && selectedClusterId === "all" && zoom < 1.3
            ? `${fullLabel.slice(0, 18)}...`
            : fullLabel;

        ctx.font = isBidder ? "bold 11px Inter, sans-serif" : "10px Inter, sans-serif";
        ctx.fillStyle = isSelected ? "#090d16" : "#334155";
        ctx.textBaseline = "top";
        ctx.fillText(truncatedLabel, pos.x, pos.y + radius + 4);

        if (isBidder && node.risk_score !== undefined && (zoom >= 1.1 || selectedClusterId !== "all")) {
          ctx.font = "9px Inter, sans-serif";
          ctx.fillStyle = "#64748b";
          ctx.fillText(`${node.risk_score.toFixed(0)}/100`, pos.x, pos.y + radius + 18);
        }
      }
    });

    ctx.restore();
  }, [
    data,
    filteredNodes,
    filteredEdges,
    nodePositions,
    selectedNode,
    hoveredNode,
    selectedClusterId,
    zoom,
    pan,
    viewMode,
    canvasSize,
  ]);

  // Click handler to select node
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || !data) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left - pan.x) / zoom;
    const clickY = (e.clientY - rect.top - pan.y) / zoom;

    let clicked: GraphNode | null = null;
    filteredNodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;
      const dist = Math.hypot(clickX - pos.x, clickY - pos.y);
      if (dist <= pos.radius + 6) {
        clicked = node;
      }
    });

    setSelectedNode(clicked);
  };

  // Hover detection
  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDraggingRef.current) {
      setPan({
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      });
      return;
    }

    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const hoverX = (e.clientX - rect.left - pan.x) / zoom;
    const hoverY = (e.clientY - rect.top - pan.y) / zoom;

    let hovered: GraphNode | null = null;
    filteredNodes.forEach((node) => {
      const pos = nodePositions.get(node.id);
      if (!pos) return;
      const dist = Math.hypot(hoverX - pos.x, hoverY - pos.y);
      if (dist <= pos.radius + 6) {
        hovered = node;
      }
    });

    setHoveredNode(hovered);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
    setSelectedClusterId("all");
    setSuspiciousOnly(false);
  };

  const fitToView = () => {
    setZoom(1.15);
    setPan({ x: 0, y: 0 });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[480px] bg-white rounded-lg border border-slate-200 text-slate-500 space-y-3">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-600">
          Synthesizing cross-bidder collusion network & relationship graph...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border border-slate-200 max-w-xl mx-auto my-8 space-y-3">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto" />
        <h3 className="text-sm font-semibold text-slate-900">Collusion Graph Unavailable</h3>
        <p className="text-xs text-slate-600">{error || "No graph data returned for this tender."}</p>
        <Button variant="outline" size="sm" onClick={fetchGraph}>
          <RotateCcw className="w-3.5 h-3.5 mr-1" /> Retry Request
        </Button>
      </div>
    );
  }

  const clusters = data.clusters || [];

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      {/* Top Header & Investigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Network className="w-4 h-4 text-blue-600" />
            Cross-Bidder Collusion & Relationship Graph
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Detects cartels, shared directors (DIN), common addresses, matching bank accounts, and IP clustering.
          </p>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-100 p-0.5 rounded-md border border-slate-200 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("graph")}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                viewMode === "graph"
                  ? "bg-white text-slate-900 shadow-xs font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Interactive Graph
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                viewMode === "table"
                  ? "bg-white text-slate-900 shadow-xs font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Table / Evidence
            </button>
          </div>
        </div>
      </div>

      {/* Cluster Filter Buttons & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-200">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-500 font-medium mr-1">Collusion Rings:</span>
          <button
            type="button"
            onClick={() => setSelectedClusterId("all")}
            className={`px-2.5 py-1 rounded border transition-colors ${
              selectedClusterId === "all"
                ? "bg-slate-900 text-white border-slate-900 font-medium"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
            }`}
          >
            All Rings ({clusters.length})
          </button>
          {clusters.map((c: CollusionCluster) => (
            <button
              key={c.cluster_id}
              type="button"
              onClick={() => setSelectedClusterId(c.cluster_id)}
              className={`px-2.5 py-1 rounded border transition-colors flex items-center gap-1.5 ${
                selectedClusterId === c.cluster_id
                  ? "bg-red-50 text-red-900 border-red-300 font-medium ring-1 ring-red-300"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
              <span className="font-mono">{c.cluster_id}</span>
              <span className="text-[10px] text-slate-500">({c.members.length} Bidders)</span>
            </button>
          ))}
        </div>

        {/* Suspicious Only Toggle */}
        <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 font-medium select-none">
          <input
            type="checkbox"
            checked={suspiciousOnly}
            onChange={(e) => setSuspiciousOnly(e.target.checked)}
            className="rounded border-slate-300 text-red-600 focus:ring-red-500"
          />
          <span>Suspicious links only</span>
        </label>
      </div>

      {/* Main Content: Graph vs Table */}
      {viewMode === "graph" ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4" ref={containerRef}>
          {/* Canvas Viewport (3 cols) */}
          <div className="lg:col-span-3 bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden relative min-h-[520px] flex flex-col">
            {/* Canvas Toolbar */}
            <div className="absolute top-3 left-3 z-10 flex items-center gap-1 bg-white/95 backdrop-blur border border-slate-200 rounded-md p-1 shadow-xs">
              <button
                type="button"
                onClick={() => setZoom((z) => Math.min(z + 0.15, 2.5))}
                className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-100"
                title="Zoom In"
                aria-label="Zoom in"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoom((z) => Math.max(z - 0.15, 0.5))}
                className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-100"
                title="Zoom Out"
                aria-label="Zoom out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <div className="w-px h-3.5 bg-slate-200" />
              <button
                type="button"
                onClick={fitToView}
                className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-100"
                title="Fit to Content"
                aria-label="Fit to content"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={resetView}
                className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-100"
                title="Reset View"
                aria-label="Reset view"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Legend */}
            <div className="absolute bottom-3 left-3 z-10 flex flex-wrap items-center gap-3 bg-white/95 backdrop-blur border border-slate-200 rounded-md px-3 py-1.5 text-[11px] text-slate-600 shadow-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-100 border border-red-500" />
                <span>High/Critical Risk Bidder</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-100 border border-emerald-500" />
                <span>Low Risk Bidder</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-100 border border-slate-500" />
                <span>Evidence Indicator</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-4 h-0.5 bg-red-600 border-b border-dashed border-red-600" />
                <span>Collusion Nexus</span>
              </div>
            </div>

            {/* Canvas */}
            <canvas
              ref={canvasRef}
              onClick={handleCanvasClick}
              onMouseDown={handleMouseDown}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleMouseUp}
              className="w-full h-[520px] cursor-grab active:cursor-grabbing"
              style={{ width: "100%", height: "520px" }}
            />
          </div>

          {/* Node / Cluster Side Detail Panel (1 col) */}
          <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-xs space-y-4">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-blue-600" />
              Investigation Details
            </h3>

            {selectedNode ? (
              <div className="space-y-3 text-xs animate-in fade-in">
                <div className="p-3 bg-slate-50 rounded-md border border-slate-200 space-y-1.5">
                  <div className="text-[10px] uppercase font-semibold text-slate-500">Selected Entity</div>
                  <div className="text-sm font-bold text-slate-900">{selectedNode.label || selectedNode.id}</div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Type: <span className="font-semibold text-slate-700">{selectedNode.type.toUpperCase()}</span>
                  </div>

                  {selectedNode.risk_score !== undefined && (
                    <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                      <span className="text-slate-600">Risk Score:</span>
                      <span className="font-mono font-bold text-slate-900">
                        {selectedNode.risk_score.toFixed(1)}/100
                      </span>
                    </div>
                  )}

                  {selectedNode.cluster_id && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-600">Collusion Cluster:</span>
                      <span className="font-mono font-bold text-red-600">{selectedNode.cluster_id}</span>
                    </div>
                  )}
                </div>

                {selectedNode.type === "bidder" && onSelectBidder && (
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full text-xs"
                    onClick={() => onSelectBidder(selectedNode.id)}
                  >
                    Open Bidder Dossier
                    <ChevronRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                )}
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-md">
                Click any node in the graph to inspect entity attributes, connected rings, and shared directorship indicators.
              </div>
            )}

            {/* Collusion Clusters Quick Summary */}
            <div className="pt-3 border-t border-slate-200 space-y-2.5">
              <div className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider">
                Identified Rings ({clusters.length})
              </div>
              {clusters.map((cluster: CollusionCluster) => (
                <div
                  key={cluster.cluster_id}
                  className="p-2.5 rounded border border-slate-200 bg-slate-50/70 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-red-700">{cluster.cluster_id}</span>
                    <Badge variant="danger">{cluster.members.length} Entities</Badge>
                  </div>
                  <div className="text-[11px] text-slate-600">
                    Indicators: {cluster.shared_indicators.join(", ")}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Members: {cluster.members.join(", ")}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Accessible Table / Evidence Fallback */
        <div className="bg-white rounded-lg border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider">
              Tabular Collusion Ring Evidence
            </h3>
            <span className="text-xs text-slate-500">Accessible non-canvas inspection</span>
          </div>

          <div className="divide-y divide-slate-200">
            {clusters.map((cluster: CollusionCluster) => (
              <div key={cluster.cluster_id} className="p-5 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                    <span className="font-mono font-bold text-sm text-slate-900">{cluster.cluster_id}</span>
                    <Badge variant="danger">{cluster.members.length} Member Entities</Badge>
                  </div>
                </div>

                <p className="text-xs text-slate-700">{cluster.description || "Shared indicators detected."}</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-2">
                  <div className="p-3 bg-slate-50 rounded border border-slate-200">
                    <span className="font-semibold text-slate-700 block mb-1">Participating Bidders:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {cluster.members.map((m: string, idx: number) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => onSelectBidder?.(m)}
                          className="px-2 py-0.5 bg-white border border-slate-300 rounded font-mono text-blue-600 hover:underline"
                        >
                          {cluster.member_names?.[idx] || m}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 rounded border border-slate-200">
                    <span className="font-semibold text-slate-700 block mb-1">Shared Indicators / Nexus:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {cluster.shared_indicators.map((ind: string) => (
                        <span
                          key={ind}
                          className="px-2 py-0.5 bg-red-50 border border-red-200 text-red-800 rounded font-mono text-[11px]"
                        >
                          {ind}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
