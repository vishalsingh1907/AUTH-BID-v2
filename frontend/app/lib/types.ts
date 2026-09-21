/**
 * SIH26100 — AuthBid Enterprise Domain Types
 * Unified contract definitions for Government e-Marketplace procurement intelligence.
 */

export interface TenderEligibilityCriteria {
  min_annual_turnover?: number;
  min_experience_years?: number;
  mse_exemption?: boolean;
  make_in_india_required?: boolean;
  make_in_india_min_percent?: number;
  oem_authorization_required?: boolean;
  emd_amount?: number;
  required_certifications?: string[];
  epfo_registration_required?: boolean;
  gst_registration_required?: boolean;
  pan_required?: boolean;
}

export interface Tender {
  tender_id: string;
  title: string;
  category: string;
  estimated_value: number;
  currency: string;
  published_date: string;
  closing_date: string;
  ministry: string;
  department: string;
  description?: string;
  eligibility_criteria?: TenderEligibilityCriteria;
  bidder_count?: number;
  verified_count?: number;
  verification_status?: "pending" | "in_progress" | "completed";
}

export interface TenderChecklistItem {
  id: string;
  category: string;
  requirement: string;
  description: string;
  mandatory: boolean;
  source: string;
  verification_method: string;
}

export interface BidderSummary {
  bidder_id: string;
  entity_name: string;
  trade_name?: string;
  entity_type: string;
  pan: string;
  gstin: string;
  bid_amount: number;
  msme_category?: string;
}

export interface BidderDirector {
  name: string;
  din?: string;
  pan?: string;
  phone?: string;
  email?: string;
}

export interface BidderAddress {
  line1: string;
  city: string;
  state: string;
  pincode: string;
}

export interface BidderBankAccount {
  bank_name: string;
  branch: string;
  ifsc: string;
  account_number?: string;
}

export interface BidderTurnover {
  year: string;
  amount: number;
}

export interface BidderDetail {
  bidder_id: string;
  entity_name: string;
  trade_name?: string;
  entity_type: string;
  identifiers: {
    pan: string;
    gstin: string;
    cin?: string;
    udyam_no?: string;
  };
  incorporation_date: string;
  registered_address: BidderAddress;
  directors: BidderDirector[];
  bank_account?: BidderBankAccount;
  gst_status: string;
  annual_turnover: BidderTurnover[];
  msme_category?: string;
  msme_valid_until?: string;
  certifications?: string[];
  epfo_registered?: boolean;
  epfo_establishment_code?: string;
  esic_registered?: boolean;
  esic_establishment_code?: string;
  startup_india_registered?: boolean;
  dipp_recognition_no?: string;
  nsic_registered?: boolean;
  itr_filed_last_3_years?: boolean;
  digilocker_verified?: boolean;
  bid_amount: number;
  make_in_india_percent?: number;
  oem_authorization?: boolean;
  oem_name?: string;
}

export interface RiskScoreComponents {
  cross_source_consistency: number;
  collusion_indicators: number;
  financial_health: number;
  document_integrity: number;
  blacklist_proximity: number;
}

export interface RiskScore {
  overall_score: number;
  compliance_score?: number;
  risk_level: "low" | "medium" | "high" | "critical";
  components: RiskScoreComponents;
  explanation: string;
}

export interface ComplianceCheck {
  check_id: string;
  check_name: string;
  category: string;
  result: "pass" | "fail" | "warning";
  details: string;
  evidence?: Array<Record<string, unknown>>;
}

export interface Anomaly {
  anomaly_id: string;
  anomaly_type: string;
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  description: string;
  related_bidders: string[];
}

export interface VerificationResult {
  bidder_id: string;
  entity_name: string;
  tender_id: string;
  status: string;
  risk_score: RiskScore;
  compliance_checks: ComplianceCheck[];
  anomalies: Anomaly[];
  hard_eligibility: Record<string, "pass" | "fail" | "warning">;
  system_recommendation?: string;
  ai_recommendation: string;
  ai_confidence?: number;
  completed_at?: string;
}

export interface VerificationSummary {
  low_risk: number;
  medium_risk: number;
  high_risk: number;
  critical_risk: number;
}

export interface VerificationResultsResponse {
  tender_id: string;
  total_bidders: number;
  results: VerificationResult[];
  summary: VerificationSummary;
}

export interface CollusionCluster {
  cluster_id: string;
  members: string[];
  member_names: string[];
  size: number;
  risk_level: string;
  shared_indicators: string[];
  description: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "bidder" | "director" | "address" | "bank" | "identifier" | "phone" | "email" | string;
  risk_level?: string;
  risk_score?: number;
  cluster_id?: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  is_suspicious?: boolean;
}

export interface GraphAnalysisSummary {
  total_bidders: number;
  total_nodes: number;
  total_edges: number;
  suspicious_edges: number;
  collusion_clusters: number;
  high_risk_bidders: number;
}

export interface GraphData {
  tender_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: CollusionCluster[];
  analysis_summary: GraphAnalysisSummary;
}

export interface AuditEntry {
  step_id: string;
  agent_id: string;
  action: string;
  input_hash: string;
  output_hash: string;
  prev_hash: string;
  current_hash: string;
  timestamp: string;
  details: {
    input_summary?: string;
    output_summary?: string;
  };
}

export interface ChainIntegrity {
  valid: boolean;
  total_blocks?: number;
  broken_block?: string;
  error?: string;
}

export interface AuditTrailResponse {
  entries: AuditEntry[];
  total_entries: number;
  chain_integrity: ChainIntegrity;
}

export interface AnchorReceipt {
  receipt_id: string;
  anchored_at: string;
  total_blocks: number;
  latest_block_id: string;
  root_hash: string;
  merkle_root: string;
  external_service: string;
  proof_type: string;
  digital_signature: string;
  status: string;
  anchored_by_role: string;
}

export interface AnchorResponse {
  latest_anchor?: AnchorReceipt;
  total_anchors: number;
  history: AnchorReceipt[];
}

export interface OfficerDecision {
  decision_id: string;
  bidder_id: string;
  tender_id: string;
  decision: "eligible" | "review" | "disqualified";
  reason: string;
  justification: string;
  officer_name: string;
  role: string;
  timestamp: string;
}

export interface ScrutinyReportSummary {
  total_bidders: number;
  recommended_for_financial_evaluation: number;
  disqualified_or_flagged: number;
  cryptographic_verification: string;
  audit_entries_count: number;
  root_hash: string;
}

export interface ScrutinyReport {
  tender_id: string;
  title: string;
  estimated_value: number;
  generated_at: string;
  committee_authority: string;
  summary: ScrutinyReportSummary;
  clean_bidders: VerificationResult[];
  disqualified_bidders: VerificationResult[];
}

export interface CopilotResponse {
  title: string;
  summary: string;
  evidence: string[];
  legal_statute: string;
  recommendation: string;
  disclaimer: string;
  context_applied?: string;
}

export interface ShowCauseNotice {
  notice_number: string;
  date: string;
  issuing_authority: string;
  tender_id: string;
  bidder: {
    bidder_id: string;
    entity_name: string;
    pan: string;
    gstin: string;
    registered_address: BidderAddress;
  };
  charges: string[];
  legal_clauses: string[];
  response_deadline_days: number;
  officer_name: string;
  officer_designation: string;
}

export interface DocumentVaultItem {
  doc_id: string;
  doc_name: string;
  verification_source: string;
  status: "verified" | "flagged" | "not_applicable";
  ocr_match_score: number;
  sha256_hash: string;
  file_size_bytes?: number;
  has_pdf?: boolean;
  download_url?: string;
  view_url?: string;
  extracted_data: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  detail?: string;
}

export interface BidderDossierViewModel {
  bidder_id: string;
  entity_name: string;
  trade_name?: string;
  entity_type: string;
  identifiers: {
    pan: string;
    gstin: string;
    cin?: string;
    udyam_no?: string;
  };
  incorporation_date: string;
  registered_address: BidderAddress;
  directors: BidderDirector[];
  bank_account?: BidderBankAccount;
  gst_status: string;
  annual_turnover: BidderTurnover[];
  msme_category?: string;
  msme_valid_until?: string;
  certifications?: string[];
  epfo_registered?: boolean;
  epfo_establishment_code?: string;
  esic_registered?: boolean;
  esic_establishment_code?: string;
  startup_india_registered?: boolean;
  dipp_recognition_no?: string;
  nsic_registered?: boolean;
  itr_filed_last_3_years?: boolean;
  digilocker_verified?: boolean;
  bid_amount: number;
  make_in_india_percent?: number;
  oem_authorization?: boolean;
  oem_name?: string;

  // Verification data (if available)
  verification_status: "pending" | "completed" | "not_run";
  risk_score?: RiskScore;
  compliance_checks?: ComplianceCheck[];
  anomalies?: Anomaly[];
  hard_eligibility?: Record<string, "pass" | "fail" | "warning">;
  system_recommendation?: string;
  ai_recommendation?: string;
  ai_confidence?: number;
  completed_at?: string;
}

export interface DossierState {
  status: "idle" | "loading" | "ready" | "not_found" | "error";
  dossier: BidderDossierViewModel | null;
  error: string | null;
}

export interface CompareState {
  isOpen: boolean;
  selectedIds: string[];
  max: number;
}

export interface GraphState {
  status: "idle" | "loading" | "ready" | "empty" | "error";
  data: GraphData | null;
  error: string | null;
  selectedNodeId: string | null;
  selectedClusterId: string | null;
  suspiciousOnly: boolean;
}
