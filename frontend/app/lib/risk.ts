/**
 * SIH26100 — AuthBid Risk Tokens & Mappings
 * Centralized risk levels, status mappings, and badge color tokens.
 */

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface RiskConfig {
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  dotColor: string;
  barColor: string;
  description: string;
}

export const RISK_CONFIG: Record<RiskLevel, RiskConfig> = {
  low: {
    label: "Low Risk",
    badgeBg: "#f0fdf4",
    badgeText: "#166534",
    badgeBorder: "#bbf7d0",
    dotColor: "#16a34a",
    barColor: "#16a34a",
    description: "Passes statutory compliance checks with zero critical anomalies.",
  },
  medium: {
    label: "Medium Risk",
    badgeBg: "#fffbeb",
    badgeText: "#92400e",
    badgeBorder: "#fde68a",
    dotColor: "#d97706",
    barColor: "#d97706",
    description: "Minor compliance observations requiring 48-hour officer clarification.",
  },
  high: {
    label: "High Risk",
    badgeBg: "#fef2f2",
    badgeText: "#991b1b",
    badgeBorder: "#fecaca",
    dotColor: "#dc2626",
    barColor: "#dc2626",
    description: "Substantial non-compliance or related party involvement detected.",
  },
  critical: {
    label: "Critical Risk",
    badgeBg: "#fef2f2",
    badgeText: "#991b1b",
    badgeBorder: "#fca5a5",
    dotColor: "#b91c1c",
    barColor: "#b91c1c",
    description: "Active collusion syndicate, shell entity, or debarment grounds detected.",
  },
};

export function getRiskLevel(score: number): RiskLevel {
  if (score >= 70) return "critical";
  if (score >= 45) return "high";
  if (score >= 20) return "medium";
  return "low";
}

export function getRiskColor(level: string | undefined | null): string {
  if (level === "critical") return "#b91c1c";
  if (level === "high") return "#dc2626";
  if (level === "medium") return "#d97706";
  return "#16a34a";
}

export function getRiskBadgeVariant(level: string | undefined | null): "success" | "warning" | "danger" | "neutral" {
  if (!level) return "neutral";
  switch (level.toLowerCase()) {
    case "low":
      return "success";
    case "medium":
      return "warning";
    case "high":
    case "critical":
      return "danger";
    default:
      return "neutral";
  }
}
