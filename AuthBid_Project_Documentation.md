# AuthBid — GeM Compliance Intelligence
## Complete Project Documentation

**Project ID:** SIH26100 | Smart India Hackathon
**Category:** AI-Powered Integrated Bid Compliance Verification & Collusion Detection Platform
**Target Domain:** Public Procurement & Bid Scrutiny on the Government e‑Marketplace (GeM)
**Document Purpose:** Complete technical and functional reference of the AuthBid codebase, intended for idea documentation, submission material, and as a source document for further content generation (e.g., NotebookLM, presentation decks, reports).

---

## Table of Contents

1. Executive Summary
2. Problem Statement
3. Proposed Solution
4. System Architecture
5. Core Functionalities (Detailed)
6. Backend Engineering Deep Dive
7. API Reference (Complete Endpoint Catalog)
8. Data Model & Schemas
9. Risk Scoring Engine — Formula & Logic
10. Collusion / Entity-Resolution Graph Engine
11. Cryptographic Audit Trail & External Anchoring
12. Role-Based Access Control (RBAC)
13. AI Copilot (Generative Layer) & Prompt-Injection Defense
14. Frontend Engineering Deep Dive
15. Sample Demonstration Dataset (12 Synthetic Bidders)
16. Technology Stack
17. Project File & Folder Structure
18. Testing Strategy & Quality Assurance
19. Deployment Architecture (Docker)
20. Security Design Notes
21. Regulatory Integration Roadmap (Path to Production)
22. Core Technical Differentiators / Unique Selling Points
23. Limitations of the Current Prototype
24. Future Scope
25. Conclusion

---

## 1. Executive Summary

**AuthBid** (internally also referenced as *BidVerify*) is an end-to-end, AI-assisted compliance verification and cartel-detection platform built for procurement officers who scrutinize vendor bids submitted on the **Government e-Marketplace (GeM)** — India's central digital procurement platform.

Today, procurement officers manually cross-check dozens of statutory documents (GST certificates, PAN cards, MCA incorporation records, MSME/Udyam certificates, balance sheets) for every bidder in every tender, and manually try to "eyeball" whether multiple bidders in the same tender are secretly related (same directors, same office address, same bank account) — a red flag for **bid-rigging and cartel formation**. This is slow, error-prone, and structurally incapable of catching sophisticated collusion patterns hidden across dozens of data fields.

AuthBid automates this entire workflow through:

- A **5-stage deterministic, rule-based verification pipeline** (not an LLM "guess") that ingests tender eligibility criteria and cross-verifies each bidder against simulated statutory registries (GST, PAN, MCA21, Udyam/MSME, and Blacklist/Debarment databases).
- An **OSINT-style entity-resolution and graph engine** that mathematically detects collusion rings by matching shared directors (DINs), shared registered addresses, shared bank accounts/IFSC codes, and shared phone numbers across competing bidders in the same tender.
- An **explainable, weighted 5-component risk scoring formula** (0–100 scale) that gives officers a transparent breakdown of *why* a bidder is risky, rather than an opaque black-box score.
- A **SHA-256 hash-chained, blockchain-style audit trail** with external "RFC 3161-style" timestamp anchoring, so that every action taken by the system (and every officer decision) is tamper-evident and cryptographically verifiable — with a live "Simulate Tampering" demonstration to prove the chain breaks visibly if altered.
- A **Generative AI Copilot** (Gemini 2.5 Flash, with a deterministic rule-based fallback) that lets officers ask natural-language questions about bidders and tenders, protected by explicit prompt-injection defenses that sandbox any untrusted bidder-submitted text.
- **Automated legal drafting** of formal Show-Cause Notices citing the exact statutory provisions violated (Competition Act 2002, General Financial Rules 2017).
- A **Role-Based Access Control (RBAC)** layer distinguishing Procurement Officers, Committee Members, and System Admins, so that only authorized roles can disqualify a bidder, tamper-test the audit chain, or publish external cryptographic anchors.

The system ships as a full-stack application: a **FastAPI (Python) backend** exposing a REST API, and a **Next.js/React (TypeScript) frontend** dashboard, both containerized via **Docker Compose**, with PostgreSQL, Neo4j, and Redis as the intended production data layer (the hackathon build uses in-memory stores with realistic synthetic data as a fallback so the whole system runs without any external database).

---

## 2. Problem Statement

Public procurement in India processes an enormous volume of tenders through GeM every year. For each tender, a procurement officer or evaluation committee must:

1. **Verify eligibility** of every bidder against dozens of statutory and financial criteria (GST registration validity, PAN name matching, minimum turnover, years of operating experience, Make-in-India domestic value addition, required certifications, OEM authorization, EPFO registration, MSME/Udyam exemptions, and blacklist/debarment status).
2. **Detect collusion / bid-rigging**, where multiple "competing" bidders are secretly controlled by the same group of people, submitting artificially different bid prices to simulate genuine competition while guaranteeing a pre-decided winner ("cover bidding").
3. **Maintain a legally defensible audit trail** of how every eligibility and disqualification decision was reached, in case the decision is challenged later (in courts, by the Central Vigilance Commission, or by the Competition Commission of India).
4. **Draft legally sound Show-Cause Notices** citing the correct statutory sections when disqualifying or debarring a vendor.

Manually, this process:
- Takes **days per tender** for a committee to complete.
- Is **highly susceptible to human error** — a shared director hidden across two 40-page corporate filings is very easy to miss.
- Provides **no cryptographic guarantee** that records were not altered after the fact by an insider.
- Produces **inconsistent, non-standardized rejection reasoning**, which weakens the government's position if a disqualified bidder appeals.

## 3. Proposed Solution

AuthBid re-imagines this workflow as an automated, explainable, and cryptographically verifiable pipeline:

- **Deterministic engines do the scrutiny** — hard eligibility checks and the composite risk score are computed by transparent, auditable rule logic and mathematics, *not* hallucinated by a language model. This is a deliberate architectural choice: anything that can affect a legal disqualification decision must be reproducible and explainable.
- **Generative AI is used only as an assistive layer** — a conversational copilot that helps officers query and understand the deterministic findings in plain English, with the underlying evidence always sourced from the rule engines, never invented.
- **Every finding carries provenance** — each extracted fact (e.g., "GST Status: Active") is tagged with its source system, a timestamp, and a confidence score, following an `Entity → Identifiers → Attributes → Documents → Source + Timestamp + Hash` canonical schema.
- **Every pipeline action is hash-chained** into an append-only audit ledger, and the current chain state can be anchored externally (e.g., to an RFC 3161 Time-Stamp Authority or a public transparency log) so that even a database administrator with full write access cannot silently rewrite history without the tampering being mathematically detectable.

---

## 4. System Architecture

AuthBid's architecture deliberately separates two categories of computation:

### 4.1 Deterministic & Rule-Based Engines (Non-LLM / Mathematically Verifiable)

| # | Engine | Responsibility |
|---|--------|-----------------|
| 1 | **Regulatory Rules Engine** | GSTN active filing check, CBDT PAN exact name matching, MCA21 incorporation & DIN scan, MSME Udyam GFR Rule 153 exemption logic, CPPP/GeM debarment check |
| 2 | **Entity Resolution & Graph Engine** | Common director DIN matching, physical address string unification, bank IFSC + account-prefix linkage, shell-company age & filing heuristic |
| 3 | **5-Vector Weighted Risk Scoring** | Cross-Source Consistency (30%), Collusion Indicators (25%), Financial Health (20%), Document Integrity (15%), Blacklist Proximity (10%) |
| 4 | **Cryptographic Audit Defense** | SHA-256 block-by-block hash chaining, Merkle-root commitment, external RFC 3161-style timestamp anchoring, tamper detection with exact block pinpointing |
| 5 | **Statutory Legal Engine** | Show-Cause Notice drafting (citing GFR Rule 151 / Competition Act Section 3(3)), Committee Scrutiny Memo generation |

### 4.2 Generative AI Component (LLM-Backed)

- **GeM Legal & Vigilance Copilot** (Gemini 2.5 Flash) — natural-language bidder intelligence and statutory cross-examination, protected by XML-style context isolation and input sanitization so bidder-submitted text can never override system instructions.

### 4.3 End-to-End Data Flow

```
GeM Tender RFP & Bids  ─┐
                        ├──▶ Regulatory Rules Engine
Bidder Documents  ──────┘         │
                                   ▼
                        Entity Resolution & Graph Engine
                                   │
                                   ▼
                        5-Vector Weighted Risk Scoring
                            │                │
                            ▼                ▼
                 Cryptographic Audit    Statutory Legal Engine
                    Chain (SHA-256)     (Show Cause Notices)
                            │                │
                            ▼                ▼
                 Procurement Officer Dashboard ◀── AI Copilot (sanitized context)
                            │
                            ├──▶ Interactive Collusion Graph (2D)
                            ├──▶ Formal Show Cause Notice
                            └──▶ Immutable Decision Audit Log
```

In plain terms: tender criteria and bidder documents flow into the regulatory rules engine, whose output feeds the entity-resolution/graph engine, which feeds the composite risk score, which in turn feeds both the cryptographic audit chain and the legal notice generator. All of this surfaces on the officer's dashboard, where the AI copilot can be consulted (with sanitized, read-only context) to explain findings in natural language, and every officer action (a decision, a tamper simulation, an anchor publish) is itself written back into the audit chain.

---

## 5. Core Functionalities (Detailed)

### 5.1 Automated Multi-Agent Verification Pipeline
Rather than a committee spending days manually examining certificates, a 5-stage sequential pipeline automates the process:

- **Agent 1 — RFP & Eligibility Ingestion:** Parses tender criteria — technical specifications, minimum annual turnover, minimum years of operational experience, and Make-in-India domestic value-addition thresholds.
- **Agent 2 — Simulated Multi-Registry Verification:**
  - **GSTN (GST Portal):** Validates active registration, jurisdiction, tax slab, and regularity of monthly GSTR-3B filings.
  - **PAN (NSDL/UTIITSL):** Verifies PAN status and performs an exact-match check against the registered corporate entity name.
  - **MCA21 (Ministry of Corporate Affairs):** Validates CIN, active Director Identification Numbers (DINs), paid-up capital, incorporation date, and registered office.
  - **Udyam/MSME Portal:** Validates Micro/Small/Medium enterprise registration to determine statutory relaxations (turnover and prior-experience exemptions under GFR Rule 153).
  - **Debarment & Blacklist Registry:** Scans against Central Public Procurement Portal (CPPP) and GeM incident-management blacklists.
- **Agent 3 — Cross-Source Consistency & Triangulation:** Cross-verifies declared financial turnover against actual GST taxable filings and ITR data to catch fabricated certificates.
- **Agent 4 — Composite Risk Scoring Engine:** Produces an explainable 0–100 score from five weighted components (detailed in Section 9).
- **Agent 5 — Cryptographic SHA-256 Audit Anchoring:** Hashes all input data, rule outputs, and determinations, chaining them cryptographically and anchoring them externally to prevent after-the-fact alteration.

### 5.2 Interactive Collusion & Knowledge Graph (`/graph`)
Cartels and shell companies frequently submit artificial "cover bids" to simulate competition. AuthBid uncovers these syndicates using an interactive 2D force-directed graph:
- **Entity Resolution** across shared directors/DINs, shared registered addresses, shared banking footprints (IFSC/account prefixes), and shared contact details (phone/email).
- **Shell-Company Heuristics** — automatically flags entities incorporated shortly before tender issuance (e.g., under ~1 year old in the implementation) with no verifiable GST filing history.
- **Graph Filters & Focus** — toggle between the full ecosystem view and a "Suspicious Only" edge view, or filter by a specific detected collusion ring/cluster.

### 5.3 Commercial Price & Spectrum Analysis
- **L1 anomaly/outlier detection** — flags abnormally low bids likely to result in contract abandonment or sub-par delivery.
- **Price clustering detection** — visualizes the spread of bid quotes to identify unnaturally tight pricing bands, a classic signature of collusive price-fixing.
- **Budget benchmark comparison** — evaluates quotes against the government's estimated tender sanction value.

### 5.4 Tamper-Evident Cryptographic Audit Trail (`/audit`)
- **SHA-256 hash-chained, blockchain-style ledger** — every pipeline action is logged as:
  `current_hash = SHA-256(prev_hash ‖ agent_id ‖ action ‖ input_hash ‖ output_hash)`
- **Live chain validation** — real-time traversal that verifies every block correctly points to the previous block's hash and that the recomputed hash matches the stored hash.
- **Interactive Tamper Simulation** — lets evaluators simulate an unauthorized database modification and immediately see the chain rupture with the exact block identified.
- **Cryptographic Restore** — demonstrates re-anchoring the chain back to a verified state.

### 5.5 Document Vault & Dossier Inspection
A digital dossier per bidder holding: GST Registration Certificate (Form REG-06), corporate PAN card, audited Balance Sheets/P&L statements, ITR-V acknowledgments, Udyam MSME registration certificate, and the Make-in-India local value-addition self-declaration. Every document carries a SHA-256 checksum, a "verified"/"flagged"/"not applicable" status badge, and an OCR-style match score, viewable inline without a mandatory download.

### 5.6 Automated Legal Show-Cause Notice Generation
Instantly drafts formal Show-Cause Notices against non-compliant or colluding bidders, citing:
- **Section 3(3) of the Competition Act, 2002** — prohibition of anti-competitive agreements, bid-rigging, and collusive bidding.
- **Rule 151 (and 175) of the General Financial Rules (GFR), 2017** — debarment for integrity offenses and falsification.
- **GeM Incident Management Policy / GTC Clause 4.14** — standard procedure for vendor blacklisting and related-party bidding.
Notices include a formal notice number, issuing authority, itemized charges, legal clauses, a response deadline, and export/print formatting for official dispatch.

### 5.7 AI Procurement Copilot
A conversational sidecar (Gemini-backed, with a reliable rule-based fallback) that lets officers query bid data in plain English — e.g., *"Why was Bidder B001 marked as critical risk?"*, *"Show all bidders exempted under the MSE category,"* or *"What is the evidence linking B001, B003, and B007?"*

### 5.8 Scrutiny Report & Decision Workflow
Officers can record remarks and assign formal statuses — **Eligible**, **Under Review / Clarification Sought**, or **Disqualified** — and generate a comprehensive **Executive Scrutiny Report** for the tender evaluation committee, summarizing technical compliance, commercial pricing, and disqualification grounds.

---

## 6. Backend Engineering Deep Dive

The backend is a **FastAPI (Python 3.12)** application located under `backend/`.

### 6.1 Application Bootstrap — `backend/main.py`
- Instantiates the FastAPI app with a `lifespan` context manager that:
  1. Runs `validate_startup_config()` (see Section 20) to check for insecure default secrets/passwords.
  2. Seeds the in-memory store with the sample tender (`SAMPLE_TENDER`).
- Registers CORS middleware (open in dev; intended to be restricted in production).
- Mounts nine routers: `tenders`, `bidders`, `verification`, `graph`, plus five mock statutory-registry routers (`gst`, `pan`, `udyam`, `mca`, `blacklist`).
- Exposes `GET /` (service metadata + endpoint map) and `GET /health` (health check).

### 6.2 Configuration — `backend/config.py`
Uses `pydantic-settings` to load configuration from environment variables / `.env`, covering:
- App metadata (`APP_NAME`, `APP_VERSION`, `DEBUG`)
- LLM configuration (`GEMINI_API_KEY`, `LLM_MODEL` = `gemini-2.5-flash`)
- PostgreSQL connection settings (with computed async/sync `DATABASE_URL` properties)
- Neo4j connection settings
- Redis URL
- Security settings (`SECRET_KEY`, JWT `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
- The external anchoring service URL (defaults to a simulated `transparency.gem.gov.in/rfc3161` endpoint)
- CORS origin allow-list

A notable engineering detail: `validate_startup_config()` maintains explicit sets of **known-insecure placeholder secrets/passwords** (e.g., `"change-this-to-a-random-secret-key-in-production"`, `"password"`, `"admin"`). If `ENVIRONMENT` is `production`/`prod` (or `STRICT_CONFIG_VALIDATION` is true) and any of these placeholders are still in use, or the `SECRET_KEY` is under 32 characters, **the application refuses to boot**, raising a `RuntimeError` that lists every violation. In development it prints a `[SECURITY WARNING]` instead of blocking startup — a deliberate "secure-by-default in prod, permissive-by-default in dev" design.

### 6.3 Data Models — `backend/models/`
- **`schemas.py`** — Pydantic v2 models defining the canonical domain schema: `Provenance`, `EntityIdentifiers`, `Director`, `Address`, `BankAccount`, `TenderCreate`/`TenderResponse`/`TenderChecklist`, `BidderSummary`/`BidderDetail`, `ComplianceCheck`, `AnomalyFlag`, `RiskScore`, `VerificationResult`, `GraphNode`/`GraphEdge`/`GraphData`, `AuditEntry`, `AgentStep`/`PipelineStatus`, plus the enums `VerificationStatus`, `RiskLevel`, `CheckResult`, and `AnomalyType`.
- **`database.py`** — For the hackathon build, this implements **in-memory data stores** (Python dicts/lists) that stand in for PostgreSQL/Neo4j so the whole system runs without external infrastructure. It exposes functions for: storing/retrieving tenders, storing/retrieving verification results, appending and reading the **hash-chained audit trail**, simulating tampering and restoring the chain, verifying chain integrity, tracking pipeline status, recording officer decisions, and recording/retrieving external anchor receipts.
- **`auth.py`** — The RBAC module (see Section 12).

### 6.4 Mock Statutory Registries — `backend/mock_apis/`
Five FastAPI routers simulate the real government verification APIs the system is designed to eventually call in production:

| File | Prefix | Simulates |
|------|--------|-----------|
| `gst_api.py` | `/api/v1/gst` | GST Portal (GSTN) — search by GSTIN, filing history, turnover derivation |
| `pan_api.py` | `/api/v1/pan` | CBDT/NSDL PAN verification and ITR summary |
| `mca_api.py` | `/api/v1/mca` | MCA21 — company lookup by CIN, director listing, and a **director cross-search by DIN** endpoint that is the backbone of collusion detection |
| `udyam_api.py` | `/api/v1/udyam` | Udyam/MSME registration verification, including category-vs-turnover validity checks |
| `blacklist_api.py` | `/api/v1/blacklist` | CPPP/GeM debarment checks, including a **"check-related-entities"** endpoint that flags a bidder if any of its directors also sit on the board of an already-blacklisted company |

- **`synthetic_data.py`** (~700 lines) is the demo data generator. It builds 12 fully-fleshed synthetic bidder companies (`B001`–`B012`) with realistic identifiers (PAN, GSTIN, CIN, Udyam numbers, DINs), a shared `SAMPLE_TENDER` record (`GEM/2026/B/4521897` — supply of 500 desktop computers, ₹2.5 Cr estimated value in this data file / ₹1.5 Cr in the docs — see Section 15 for the exact reconciled scenario), monthly GST filing histories generated programmatically (with deliberate "gaps" for specific bidders), and a `BLACKLIST_DATABASE` of historically debarred entities. Two collusion rings and several standalone anomalies are **deliberately planted** into this dataset so the detection engines have real patterns to surface (see Section 15).

### 6.5 Routers — `backend/routers/`

- **`tenders.py`** — CRUD-style read endpoints for tenders: list tenders, get tender detail (with computed bidder summaries), and get the AI-generated compliance checklist for a tender.
- **`bidders.py`** — List all bidders, get a single bidder's full profile, and get a bidder's verification result for a specific tender.
- **`verification.py`** (the largest and most important router, ~950 lines) — implements:
  - `_run_compliance_checks()` — 11 discrete compliance checks per bidder (GST registration, PAN name match, turnover, experience years, Make-in-India %, certifications, OEM authorization, EPFO registration, MSME validity, blacklist status, GST filing compliance).
  - `_detect_anomalies()` — 7 categories of cross-bidder anomaly detection (director overlap, address overlap, bank overlap, phone overlap, shell-company heuristic, GST filing gaps, turnover decline).
  - `_calculate_risk_score()` — the 5-component weighted risk formula (see Section 9).
  - `_generate_risk_explanation()` — turns the score and detected anomalies into a natural-language explanation string.
  - `_sanitize_bidder_input()` — the prompt-injection defense function (see Section 13).
  - Route handlers for: running the full pipeline (`POST /run/{tender_id}`), fetching results, fetching/tampering/restoring/anchoring the audit trail, recording and listing officer decisions, generating the scrutiny report, the AI copilot endpoint, Show-Cause Notice generation, and the document-vault endpoint.
- **`graph.py`** — Builds both a per-bidder entity graph (`_build_bidder_graph`) and, more importantly, the **cross-bidder collusion graph** (`_build_cross_bidder_graph`) that performs connected-component analysis (a breadth-first search over shared directors/addresses/phones) to automatically cluster bidders into collusion "rings" and mark which graph edges are "suspicious" (i.e., shared with more than one bidder).

---

## 7. API Reference (Complete Endpoint Catalog)

All endpoints are served under `http://localhost:8000` in local development, with interactive Swagger docs auto-generated at `/docs`.

### 7.1 Core Domain Endpoints

| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/` | Service metadata and endpoint map |
| GET | `/health` | Health check |
| GET | `/api/tenders` | List all tenders |
| GET | `/api/tenders/{tender_id}` | Tender detail with bidder summaries |
| GET | `/api/tenders/{tender_id}/checklist` | AI-generated compliance checklist |
| GET | `/api/bidders` | List all bidders |
| GET | `/api/bidders/{bidder_id}` | Full bidder profile |
| GET | `/api/bidders/{bidder_id}/verification/{tender_id}` | Bidder verification result for a tender |
| POST | `/api/verification/run/{tender_id}` | Run the full verification pipeline for all bidders in a tender |
| GET | `/api/verification/results/{tender_id}` | All verification results + risk-level summary for a tender |
| GET | `/api/verification/audit-trail` | Full hash-chained audit trail + live integrity check |
| POST | `/api/verification/tamper` | **[Admin only]** Simulate tampering with an audit entry |
| POST | `/api/verification/restore` | **[Admin only]** Restore/re-anchor cryptographic integrity |
| POST | `/api/verification/anchor` | **[Officer/Admin]** Publish an external Merkle-root anchor receipt |
| GET | `/api/verification/anchor` | Fetch the latest (and historical) anchor receipts |
| POST | `/api/verification/decision` | **[Officer/Admin]** Record a formal eligibility/disqualification decision |
| GET | `/api/verification/decisions/{tender_id}` | List all recorded officer decisions for a tender |
| GET | `/api/verification/report/{tender_id}` | Generate the Executive Scrutiny Report |
| POST | `/api/verification/copilot` | AI Copilot natural-language query |
| GET | `/api/verification/show-cause/{bidder_id}` | **[Officer/Admin]** Generate a formal Show-Cause Notice |
| GET | `/api/verification/documents/{bidder_id}` | Digital document vault for a bidder |
| GET | `/api/graph/bidder/{bidder_id}` | Entity graph for a single bidder |
| GET | `/api/graph/collusion/{tender_id}` | Full cross-bidder collusion graph + detected clusters |

### 7.2 Simulated Statutory Registry Endpoints

| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/api/v1/gst/search/{gstin}` | GSTIN → legal name, status, registration date |
| GET | `/api/v1/gst/filing-history/{gstin}` | Monthly GSTR-3B filing history + compliance rate |
| GET | `/api/v1/gst/turnover/{gstin}` | GST-derived turnover vs. self-declared turnover |
| GET | `/api/v1/pan/verify/{pan}` | PAN → name match, status, Aadhaar linkage |
| GET | `/api/v1/pan/itr-summary/{pan}` | ITR filing summary cross-referenced with turnover |
| GET | `/api/v1/mca/company/{cin}` | MCA21 company master data (incorporation age, capital) |
| GET | `/api/v1/mca/directors/{cin}` | Directors of a company |
| GET | `/api/v1/mca/director-search/{din}` | **Cross-company director search** — flags `is_common_director` |
| GET | `/api/v1/udyam/verify/{udyam_no}` | Udyam/MSME registration validity and category check |
| GET | `/api/v1/blacklist/check/{identifier}` | Blacklist/debarment lookup by PAN, GSTIN, or name |
| GET | `/api/v1/blacklist/check-related/{pan}` | Flags blacklisted **related** entities via shared directors |

**Access control note:** All endpoints accept an `X-User-Role` header (`officer` | `committee_member` | `admin`) which the RBAC layer inspects for permission-gated actions (see Section 12). If omitted, the system defaults to `officer` in development.

---

## 8. Data Model & Schemas

AuthBid follows a canonical entity model of:
**Entity → Identifiers → Attributes → Documents → Source + Timestamp + Hash**

Key Pydantic schemas (from `backend/models/schemas.py`):

- **`Provenance`** — every extracted field can carry `source` (e.g., `GST_PORTAL`, `PAN_NSDL`, `MCA21`), an optional `document_id`, a `timestamp`, a `confidence` score (0–1), and a `hash`.
- **`EntityIdentifiers`** — `pan`, `gstin`, `cin`, `udyam_no`, and a list of `din_list` (Director Identification Numbers).
- **`Director`** — `name`, `din`, `pan`, `phone`, `email`, `designation`.
- **`Address`** — `line1`, `line2`, `city`, `state`, `pincode`.
- **`BankAccount`** — `bank_name`, `ifsc`, `account_no`, `branch`.
- **`BidderDetail`** — the full bidder record combining identifiers, address, directors, bank account, bid amount, annual turnover history, certifications, GST/MSME status, Make-in-India percentage, and OEM authorization.
- **`ComplianceCheck`** — a single named check (e.g., "GST Registration") with a `result` (`pass`/`fail`/`warning`/`not_applicable`), human-readable `details`, and an `evidence` list.
- **`AnomalyFlag`** — a detected anomaly with an `anomaly_type` enum (`collusion_ring`, `shell_company`, `pan_name_mismatch`, `gst_filing_gap`, `expired_msme`, `previously_debarred`, `turnover_inconsistency`, `address_overlap`, `director_overlap`, `bank_overlap`, `phone_overlap`), a `severity` (`low`/`medium`/`high`/`critical`), and `related_bidders`.
- **`RiskScore`** — `overall_score` (0–100), `risk_level`, a `components` breakdown dict, and a natural-language `explanation`.
- **`VerificationResult`** — the complete per-bidder verification record combining risk score, all compliance checks, all anomalies, hard eligibility summary, AI recommendation text, AI confidence, and an evidence chain.
- **`GraphNode`/`GraphEdge`/`GraphData`** — the collusion-graph representation, where nodes can be of type `bidder`, `director`, `address`, `bank`, or `identifier`, and edges carry a `relationship` label (`HAS_DIRECTOR`, `REGISTERED_AT`, `BANKS_WITH`, `HAS_IDENTIFIER`) plus an `is_suspicious` boolean.
- **`AuditEntry`** — `step_id`, `agent_id`, `action`, `input_hash`, `output_hash`, `prev_hash`, `timestamp`, `details`.
- **`PipelineStatus`/`AgentStep`** — tracks the progress of the multi-agent pipeline per bidder/tender.

---

## 9. Risk Scoring Engine — Formula & Logic

The composite risk score (implemented in `_calculate_risk_score()` in `verification.py`) is a **0–100 explainable score** built from five independently-weighted components:

| Component | Weight | What Drives It |
|-----------|--------|-----------------|
| **Cross-Source Consistency** | 30% | Number of failed (`×100`) and warning (`×40`) compliance checks, normalized by total checks run |
| **Collusion Indicators** | 25% | Count of collusion-type anomalies (director/address/bank/phone overlap), capped at 4 anomalies = 100 raw score |
| **Financial Health** | 20% | 80 raw points if no turnover data exists at all; 50 raw points if the latest year's turnover dropped more than 30% vs. the prior year |
| **Document Integrity** | 15% | +50 raw points if flagged as a shell company; +30 raw points if GST filing gaps exist (capped at 100) |
| **Blacklist Proximity** | 10% | 100 raw points if actively blacklisted; 50 raw points if there is blacklist *history* without active status |

**Formula:**
```
overall_score =  (consistency_raw × 0.30)
               + (collusion_raw   × 0.25)
               + (financial_raw   × 0.20)
               + (document_raw    × 0.15)
               + (blacklist_raw   × 0.10)
```
The result is clamped to a maximum of 100 and rounded to 1 decimal place.

**Risk-level thresholds** (also verified by an explicit unit test):

| Score Range | Risk Level |
|-------------|------------|
| ≥ 70 | 🔴 **Critical** |
| ≥ 45 and < 70 | 🟠 **High** |
| ≥ 20 and < 45 | 🟡 **Medium** |
| < 20 | 🟢 **Low** |

Every score is accompanied by a `_generate_risk_explanation()` output — a natural-language summary (e.g., *"⚠️ CRITICAL RISK (Score: 82.5/100). Potential collusion detected with 2 other bidder(s) in this tender. Entity shows shell company characteristics (recent incorporation, no filing history). 2 mandatory eligibility check(s) failed: OEM Authorization, Certifications."*) — so the officer never has to guess why a number is what it is.

### 9.1 The 11 Compliance Checks Feeding the Consistency Score
GST Registration · PAN Verification (name-match) · Annual Turnover (with MSE exemption logic) · Experience (years since incorporation) · Make-in-India percentage · Certifications held vs. required · OEM Authorization · EPFO Registration · MSME Registration validity · Blacklist/Debarment status · GST Filing Compliance (last 12 months).

### 9.2 The 7 Anomaly Detectors Feeding the Collusion & Document-Integrity Scores
1. **Director overlap** — any shared DIN/PAN between two bidders' director lists → `critical` severity.
2. **Address overlap** — identical registered address JSON → `high` severity.
3. **Bank overlap** — same IFSC code *and* matching first 10 digits of account number → `high` severity.
4. **Phone overlap** — any shared director phone number → `high` severity.
5. **Shell company detection** — incorporated less than 365 days ago *and* zero GST filing history → `critical` severity.
6. **GST filing gaps** — any "Not Filed" periods in the last 12 months → `medium` severity.
7. **Turnover decline** — latest year's turnover is less than 70% of the prior year's → `medium` severity.

---

## 10. Collusion / Entity-Resolution Graph Engine

Implemented in `backend/routers/graph.py`, this is described in the codebase itself as **"the SHOWSTOPPER endpoint."**

**How it builds the cross-bidder graph:**
1. Every bidder becomes a graph node, pre-colored by risk level (derived from any pre-tagged `anomalies` list in the synthetic data: shell company or Ring-1 membership → `critical`; Ring-2 membership or prior debarment → `high`; filing gaps/expired MSME/PAN mismatch → `medium`; otherwise → `low`).
2. Every director, registered address, and bank branch becomes its own node, and every bidder is connected to its own directors/address/bank/identifiers via labeled edges (`HAS_DIRECTOR`, `REGISTERED_AT`, `BANKS_WITH`, `HAS_IDENTIFIER`).
3. Any node (director, address, or bank branch) that is shared by **more than one bidder** has all of its connecting edges marked `is_suspicious = true` — this is the visual/analytical signal of a potential cartel link.
4. **Cluster detection** then runs a breadth-first search (connected-component analysis) over a same-bidder adjacency map built from shared directors, shared addresses, shared bank branches, shared phone numbers, and shared emails. Any connected component with more than one bidder becomes a labeled **collusion cluster** (e.g., `CLU-001`), complete with a human-readable list of `shared_indicators` (e.g., "Shared director (DIN/PAN: 09876543)", "Shared registered address", "Shared bank branch (IFSC: PUNB0123400)", "Shared phone number") and a generated description ("Potential bid-rigging ring: TechVision Solutions, DigiCore Infosystems, Quantum Digital Services").
5. The API response also returns an `analysis_summary` — total bidders, total nodes/edges, count of suspicious edges, number of collusion clusters found, and the count of high/critical-risk bidders — so the frontend can render top-line statistics without recomputing anything client-side.

On the frontend, this graph renders as an **interactive 2D force-directed graph** (via `react-force-graph-2d`), with filters to show the full ecosystem or only the suspicious subgraph, and the ability to focus on a single detected ring.

---

## 11. Cryptographic Audit Trail & External Anchoring

### 11.1 Internal Hash Chain
Every pipeline action (a compliance check batch, an anomaly-detection pass, a risk-scoring event, an officer decision, a tamper simulation, an anchor publish) is appended to an in-memory ledger via `append_audit_entry(agent_id, action, input_data, output_data)`. Each entry computes:

```
input_hash    = SHA-256(json(input_data))
output_hash   = SHA-256(json(output_data))
current_hash  = SHA-256(prev_hash ‖ agent_id ‖ action ‖ input_hash ‖ output_hash)
```

The very first entry's `prev_hash` is the literal string `"GENESIS"`. Every subsequent entry's `prev_hash` must equal the previous entry's `current_hash` — this is what makes the ledger a **hash chain**: altering any single field in any historical entry changes that entry's `current_hash`, which breaks the link to the *next* entry, and so on down the chain.

### 11.2 Chain Verification
`verify_audit_chain()` walks the entire chain, checking (a) that each entry's stored `prev_hash` matches the actual previous entry's `current_hash`, and (b) that recomputing the hash from the entry's own fields reproduces the stored `current_hash`. If either check fails, it returns `{"valid": false, "broken_at": <step_id>, "reason": ...}`, pinpointing the exact tampered block.

### 11.3 Tamper Simulation & Restore
For demonstration purposes, `POST /api/verification/tamper` (admin-only) intentionally corrupts one entry's `action` field and recomputes a bogus `input_hash`, **without** recomputing the downstream chain — so the very next chain-verification call immediately reports a break. `POST /api/verification/restore` (admin-only) either rolls back to a backed-up copy of the original chain, or rebuilds the entire chain's hashes from `GENESIS` forward, restoring cryptographic validity.

### 11.4 External Anchoring
Because a hash chain stored **inside the same database** is only *tamper-evident*, not *tamper-proof* against an administrator with full write access (who could, in theory, recompute the entire chain after an edit), AuthBid implements **external anchoring** (`POST /api/verification/anchor`, Officer/Admin only):

1. Computes a Merkle-style root over all current block hashes: `merkle_root = SHA-256("hash1|hash2|...|hashN")`.
2. Packages a receipt: `receipt_id`, `anchored_at`, `total_blocks`, `latest_block_id`, `root_hash`, `merkle_root`, the configured `external_service` URL (defaults to a simulated `https://transparency.gem.gov.in/rfc3161`), a `proof_type` label ("RFC-3161 Time-Stamp Protocol / Transparency Log Manifest"), and a `digital_signature` (a truncated SHA-256 signature stand-in).
3. Records the receipt and logs an `EXTERNAL_ANCHOR_PUBLISHED` entry back into the audit chain itself.

The design document `docs/AUDIT_ANCHORING.md` elaborates the target production architecture across three real-world anchoring channels:
- **Channel 1 — RFC 3161 Qualified Time-Stamp Authority:** submit the Merkle root as a `TimeStampReq` to an accredited TSA (e.g., NIC or eMudhra), receiving a signed `TimeStampToken` proving the state existed at a certified point in time.
- **Channel 2 — Append-only Transparency Logs (RFC 6962-style, e.g., Sigstore/Rekor/Trillian):** publish the root to a public, append-only log where inclusion proofs are independently queryable.
- **Channel 3 — National Public Distributed Ledger:** periodic batch commitment of the Merkle root to a sovereign permissioned blockchain (e.g., a MeitY/NIC-hosted framework), keeping cost negligible since only one 32-byte hash is anchored per verification cycle.

---

## 12. Role-Based Access Control (RBAC)

Implemented in `backend/models/auth.py`. Three roles are defined:

| Role | Value | Typical Permissions |
|------|-------|----------------------|
| **Officer** | `officer` | Full decision rights — record eligibility/disqualification decisions, generate Show-Cause Notices, publish external anchors |
| **Committee Member** | `committee_member` | Advisory review — can view results, notes, and the audit trail, but **cannot** finalize disqualifications or generate legal notices |
| **Admin** | `admin` | System administration / CVO-level — tamper simulation, restore, anchoring, and all officer-level actions |

The active role is read from the `X-User-Role` HTTP header on every request (defaulting to `officer` in development if omitted). The `require_roles([...])` dependency factory is applied to sensitive endpoints; if the caller's role isn't in the allowed list, the API returns **HTTP 403 Forbidden** with a message explicitly citing GFR 2017 and GeM policy as the basis for the restriction. This is unit-tested (`test_rbac_and_anchoring.py`) to confirm, for example, that a `committee_member` is blocked from generating a Show-Cause Notice or finalizing a disqualification, while an `officer` can do both.

Endpoints gated by role:
- `POST /api/verification/tamper` — **Admin only**
- `POST /api/verification/restore` — **Admin only**
- `POST /api/verification/anchor` — **Officer or Admin**
- `POST /api/verification/decision` — **Officer or Admin**
- `GET /api/verification/show-cause/{bidder_id}` — **Officer or Admin**

---

## 13. AI Copilot (Generative Layer) & Prompt-Injection Defense

The copilot endpoint (`POST /api/verification/copilot`) is the system's only LLM-facing surface, intended to run on **Gemini 2.5 Flash** via LangChain/LangGraph (with the hackathon build using rich rule-based canned responses as a reliable fallback/demo path so the feature works even without a live API key).

**Prompt-injection defense (`_sanitize_bidder_input`):**
- Any untrusted text (the officer's query, or bidder-submitted text later interpolated into a prompt) is passed through a regex filter that detects and neutralizes common injection phrases — case-insensitively matching patterns like *"ignore previous instructions,"* *"system prompt,"* `system:`, `developer:`, `[INST]`, or `<|im_start|>` — replacing them with the literal marker `[SUSPICIOUS_DIRECTIVE_REMOVED]`.
- Markdown code fences (` ``` `) are neutralized (replaced with `'''`) to prevent prompt "breakout" via fenced blocks.
- Input is hard-truncated to 1200 characters.
- When bidder-specific context is included in a copilot response, it is wrapped in an explicit, clearly-labeled XML-style tag: `<untrusted_bidder_context source="uploaded_dossier" bidder_id="..." sanitized="true">...</untrusted_bidder_context>` — visually and structurally isolating it from system instructions, following the principle that an LLM should be able to distinguish "data to reason about" from "instructions to obey."
- This sanitizer is directly unit-tested (`test_llm_prompt_injection_sanitization` in `test_rbac_and_anchoring.py`).

**Example copilot capabilities (with rule-based canned intelligence for the demo dataset):**
- Deep-dive analysis of "Collusion Ring 1" and "Collusion Ring 2," citing specific DINs, shared addresses, and legal statutes.
- Shell-company forensic reports (age, filing history, UDIN validity, director nexus).
- L1 (lowest-bid) commercial evaluation recommendations that account for disqualified/flagged bidders.
- A general fallback answer summarizing total bidders, detected rings, and audit-chain status for any unmatched query.

Every AI response explicitly includes a `disclaimer` field: *"AI-generated analysis — verify independently against statutory records before making legal determinations."* — reinforcing that the AI is advisory, not authoritative.

---

## 14. Frontend Engineering Deep Dive

The frontend is a **Next.js 16 (App Router, Turbopack) + React 19 + TypeScript** single-page application under `frontend/`.

### 14.1 Structure
- `app/page.tsx` — the main dashboard (a very large, feature-dense client component, ~2,000+ lines) implementing six primary views via a `view` state variable: **`dashboard`**, **`bidders`**, **`graph`**, **`checklist`**, **`audit`**, and **`report`**.
- `app/lib/api.ts` — a thin typed fetch wrapper (`fetchAPI`) that automatically attaches the `X-User-Role` header to every request based on the currently selected role (`officer`/`committee_member`/`admin`), plus a fully typed `api` object exposing one method per backend endpoint (tenders, bidders, verification run/results, audit trail, tamper/restore/anchor, decisions, scrutiny report, copilot query, show-cause notice, document vault, and graph endpoints).
- `app/components/` — focused, reusable components:
  - **`BidderCompareModal.tsx`** — side-by-side comparison of multiple bidders' compliance checks and risk scores.
  - **`CommercialPriceAnalysis.tsx`** — visualizes bid-price clustering/outlier analysis against risk levels.
  - **`CopilotDrawer.tsx`** — the chat-style AI Copilot UI (message list, input box, evidence/legal-statute/recommendation rendering).
  - **`DocumentVault.tsx`** — renders each bidder's document dossier with checksum display, copy-to-clipboard, and verified/flagged badges.
  - **`ShowCauseModal.tsx`** — renders the generated Show-Cause Notice in an official letter format with print/download/copy actions.
- Internal helper components in `page.tsx` include `RiskBadge`, `RiskGauge` (a visual 0–100 gauge), `StatCard` (dashboard KPI tiles), a currency formatter, and `EnterpriseGraphCanvas` (the custom force-directed graph renderer for the collusion view).
- A `dossierTab` state (`overview` | `documents` | `checklist` | `anomalies`) drives a tabbed per-bidder detail dossier within the bidder view.

### 14.2 Key Interaction Flows
- Officers can filter bidders by risk level (`riskFilter`), record free-text officer notes and formal decisions (`officerNotes`, `officerDecisions`) per bidder, and compare up to several bidders at once via `selectedCompareIds`.
- The collusion graph view supports filtering by a specific detected cluster (`selectedClusterFilter`).
- The audit view shows the live hash chain, lets an Admin trigger the tamper simulation, and lets an Officer/Admin trigger external anchoring — all backed 1:1 by the corresponding API calls.

### 14.3 Styling & UX
Built with **TailwindCSS v4**, **Lucide React** icons, **Recharts** for charts, and **react-force-graph-2d** for the network visualization — giving the dashboard a modern, data-dense "enterprise command console" aesthetic appropriate for a government back-office tool.

---

## 15. Sample Demonstration Dataset (12 Synthetic Bidders)

**Tender Reference:** `GEM/2026/B/4521897` — *Supply of 500 Desktop Computers with 3-Year On-Site Warranty*
**Estimated Value:** ₹2,50,00,000 (₹2.50 Crore / 25,000,000 INR), as defined canonically in `backend/mock_apis/synthetic_data.py`.

The dataset (seeded with `random.seed(42)` for full reproducibility) plants two collusion rings and several standalone anomalies:

| Bidder ID | Entity Name | Bid Amount | Placed Finding / Anomaly | Risk Level |
|-----------|-------------|------------|----------------------------|------------|
| **B001** | TechVision Solutions Pvt. Ltd. | ₹2,35,00,000 | **Collusion Ring 1**: Shared directors (DIN: 09876543, 08765432) & address with B003 & B007 | 🔴 Critical |
| **B002** | Reliable Computing Systems Ltd. | ₹2,42,00,000 | Clean bidder; valid MSME, GST, and MCA records; compliant BIS & ISO | 🟢 Low |
| **B003** | DigiCore Infosystems Pvt. Ltd. | ₹2,48,00,000 | **Collusion Ring 1**: Shared directors with B001 & B007 | 🔴 Critical |
| **B004** | GreenTech Peripherals | ₹2,28,00,000 | Expired MSME registration (expired 2025-12-31); under scrutiny for MSE relaxation | 🟡 Medium |
| **B005** | NexGen IT Solutions Pvt. Ltd. | ₹2,39,00,000 | **Collusion Ring 2**: Shared bank branch (PNB, IFSC: PUNB0123400) & director phone with B009 | 🔴 High |
| **B006** | Bharat Electronics & Computing | ₹2,45,00,000 | PAN registered name typo mismatches GST legal entity name | 🟡 Medium |
| **B007** | Quantum Digital Services Pvt. Ltd. | ₹2,20,00,000 | **Collusion Ring 1**: Shell company (<90 days old, zero GST history) submitting cover bid | 🔴 Critical |
| **B008** | MegaByte Computers Pvt. Ltd. | ₹2,40,00,000 | Historical debarment record on MoD/GeM incident database (status cleared) | 🟡 Medium |
| **B009** | CloudFirst Technologies Pvt. Ltd. | ₹2,32,00,000 | **Collusion Ring 2**: Shared bank branch (PNB, IFSC: PUNB0123400) & contact phone with B005 | 🔴 High |
| **B010** | Pinnacle Systems India Pvt. Ltd. | ₹2,48,00,000 | Clean bidder; fully compliant ISO 9001:2015, ISO 27001, BIS certified | 🟢 Low |
| **B011** | ByteWave Electronics Pvt. Ltd. | ₹2,30,00,000 | Non-compliance in GST (2 unfiled GSTR-3B return periods) | 🟡 Medium |
| **B012** | Atlas Infosys Solutions Pvt. Ltd. | ₹2,46,00,000 | Clean bidder; fully verified domestic manufacturer (MII 68%) | 🟢 Low |

*(Note: The master synthetic dataset in `synthetic_data.py`, the AI Copilot responses in `verification.py`, frontend default views, and all documentation now reference this identical canonical dataset.)*

---

## 16. Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | Next.js 16 (App Router, Turbopack), React 19, TypeScript, TailwindCSS v4, Lucide-React, Recharts, React-Force-Graph-2D |
| **Backend** | FastAPI 0.115, Python 3.12, Pydantic v2, Uvicorn, Python-Multipart |
| **Database & Cache** | PostgreSQL 17 (AsyncPG/SQLAlchemy 2.0, Alembic migrations) — production target; Neo4j 5 (graph DB) — production target; Redis 7 (Celery broker / cache), with **in-memory fallback stores** used for the hackathon demo build |
| **AI / NLP** | Google Gemini API (`gemini-2.5-flash`), LangChain, LangGraph, LangChain-Community, LangChain-Google-GenAI |
| **Document Intelligence (planned/available)** | pdf2image, Pillow, pyzbar (barcode/QR reading) |
| **Task Queue (planned)** | Celery with Redis broker |
| **Security & Integrity** | SHA-256 hash chaining, cryptographic verification, CORS, python-jose (JWT), passlib/bcrypt |
| **Utilities** | httpx, aiofiles, networkx, numpy |
| **Tooling** | Ruff (linting, `pyproject.toml`), ESLint, pytest |
| **Deployment** | Docker & Docker Compose (separate dev and production compose files) |

---

## 17. Project File & Folder Structure

```
AuthBid-main/
├── README.md                          — Quick start & architecture overview
├── FEATURES.md                        — Full functionality & architecture reference
├── CONTRIBUTING.md                    — Contributor setup & QA guide
├── LICENSE
├── pyproject.toml                     — Ruff lint configuration
├── docker-compose.yml                 — Local development stack
├── docker-compose.prod.yml            — Production stack (multi-worker, restart policies)
├── docs/
│   ├── AUDIT_ANCHORING.md             — Cryptographic anchoring architecture
│   └── REGULATORY_INTEGRATION_ROADMAP.md — Path to live statutory API integration
├── backend/
│   ├── main.py                        — FastAPI app entrypoint
│   ├── config.py                      — Settings + startup security validation
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── models/
│   │   ├── schemas.py                 — Pydantic domain schemas
│   │   ├── database.py                — In-memory stores + hash-chain logic
│   │   └── auth.py                    — RBAC roles & dependencies
│   ├── routers/
│   │   ├── tenders.py
│   │   ├── bidders.py
│   │   ├── verification.py            — Core pipeline, risk scoring, copilot, audit
│   │   └── graph.py                   — Entity resolution & collusion graph
│   ├── mock_apis/
│   │   ├── synthetic_data.py          — 12-bidder demo dataset generator
│   │   ├── gst_api.py
│   │   ├── pan_api.py
│   │   ├── mca_api.py
│   │   ├── udyam_api.py
│   │   └── blacklist_api.py
│   └── tests/
│       ├── conftest.py
│       ├── test_collusion_rules.py
│       ├── test_config_validation.py
│       ├── test_hash_chain.py
│       ├── test_pipeline_integration.py
│       ├── test_rbac_and_anchoring.py
│       └── test_risk_scoring.py
└── frontend/
    ├── package.json
    ├── Dockerfile
    ├── next.config.ts
    ├── tsconfig.json
    └── app/
        ├── page.tsx                   — Main dashboard (all 6 views)
        ├── layout.tsx
        ├── globals.css
        ├── lib/
        │   └── api.ts                 — Typed API client
        └── components/
            ├── BidderCompareModal.tsx
            ├── CommercialPriceAnalysis.tsx
            ├── CopilotDrawer.tsx
            ├── DocumentVault.tsx
            └── ShowCauseModal.tsx
```

---

## 18. Testing Strategy & Quality Assurance

The backend ships a `pytest` suite under `backend/tests/`, run via `python -m pytest backend/tests -v`, covering:

- **`test_collusion_rules.py`** — director overlap, address overlap, bank overlap, phone overlap, and shell-company detection, each verified to produce the correct anomaly type and severity.
- **`test_config_validation.py`** — confirms production startup *passes* with secure custom credentials, *fails* (raises `RuntimeError`) with default `SECRET_KEY` or default DB passwords, and only *warns* (doesn't crash) in development mode.
- **`test_hash_chain.py`** — verifies the genesis block's `prev_hash` is `"GENESIS"` and each subsequent block correctly links to the prior block's hash; verifies that tampering causes `verify_audit_chain()` to report the exact `broken_at` block; verifies that `restore_audit_trail()` repairs the chain.
- **`test_pipeline_integration.py`** — an end-to-end test running the full verification pipeline against the entire synthetic 12-bidder dataset.
- **`test_rbac_and_anchoring.py`** — confirms an `officer` can generate a Show-Cause Notice while a `committee_member` is forbidden from doing so and from finalizing a disqualification; confirms disqualification requires a mandatory reason/justification (HTTP 400 otherwise); confirms external anchoring correctly publishes a cryptographic commitment; and confirms the prompt-injection sanitizer strips known attack phrases.
- **`test_risk_scoring.py`** — a fully worked-out set of unit tests validating each of the 5 weight contributions individually (e.g., "4 collusion anomalies cap at 100 raw score and contribute 25 points at 25% weight"; "missing turnover contributes 80 × 0.20 = 16.0 points") and the exact risk-level threshold cutoffs (critical ≥ 70, high ≥ 45, medium ≥ 20, low < 20).

Linting is enforced via **Ruff** (`pyproject.toml`, targeting Python 3.12, 120-character line length) for the backend and **ESLint** for the frontend, both expected to pass before a PR merges (per `CONTRIBUTING.md`).

---

## 19. Deployment Architecture (Docker)

Two Docker Compose files are provided:

### 19.1 `docker-compose.yml` (Development)
Spins up **PostgreSQL 17 (Alpine)**, **Neo4j 5 Community** (with the APOC plugin), **Redis 7 (Alpine)**, the **FastAPI backend** (hot-reload via `uvicorn --reload`, source mounted as a volume), and the **Next.js frontend** (`npm run dev`, source mounted as a volume). Health checks are defined for all three data services, and the backend/frontend both depend on their health before starting.

### 19.2 `docker-compose.prod.yml` (Production)
The same service topology, but:
- All credentials are parameterized via environment variables (`${POSTGRES_PASSWORD:-...}`, etc.) rather than hardcoded.
- `ENVIRONMENT=production` and `STRICT_CONFIG_VALIDATION=true` are set, activating the hard startup security check in `config.py` (the app will refuse to boot if default secrets remain).
- The backend runs with **4 Uvicorn workers** and no auto-reload.
- The frontend runs a compiled production build (`NODE_ENV=production`) rather than the dev server.
- All services carry a `restart: unless-stopped` policy for resilience.

### 19.3 Quick Local Run (Without Docker)
```powershell
# Backend
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd frontend
npm run dev
```
Frontend: `http://localhost:3000` · Backend: `http://localhost:8000` · Swagger docs: `http://localhost:8000/docs`

---

## 20. Security Design Notes

- **Secure-by-default in production, permissive-by-default in development:** `validate_startup_config()` maintains explicit deny-lists of known-insecure placeholder secrets and database passwords; production mode refuses to boot on a match, development mode only warns.
- **RBAC on every state-changing/sensitive endpoint:** tamper simulation and chain restoration are Admin-only; decisions, Show-Cause Notices, and external anchoring require Officer or Admin.
- **Mandatory justification for disqualification:** the API enforces (HTTP 400 if missing) that any `"disqualified"` decision includes both a categorical `reason` and a `justification` of meaningful length — preventing arbitrary, undocumented rejections that could be successfully challenged later.
- **Prompt-injection isolation:** all untrusted text reaching the LLM copilot is regex-filtered for known injection patterns, code-fence-neutralized, length-capped, and wrapped in an explicit "untrusted context" tag before being combined with system instructions.
- **CORS:** wide-open (`allow_origins=["*"]`) in the current build, explicitly flagged in code comments as **"Dev mode — restrict in production."**
- **Cryptographic tamper-evidence:** the SHA-256 hash chain plus external Merkle-root anchoring together defend not just against external attackers but against a **malicious insider with database write access** — the core threat model documented in `docs/AUDIT_ANCHORING.md`.
- **Simulated-data transparency:** the regulatory roadmap explicitly plans for UI badges (`[SIMULATED DEMO REGISTRY]`), document watermarks (`"DEMO DATA — SYNTHETIC RECORD FOR EVALUATION"`), and audit-trail `source: "SIMULATED_SANDBOX"` tagging, so that no one can mistake demo output for live regulatory data prior to production certification.

---

## 21. Regulatory Integration Roadmap (Path to Production)

The current build uses deterministic **mock APIs** in place of live government registries. `docs/REGULATORY_INTEGRATION_ROADMAP.md` lays out the exact production integration plan:

| Registry | Production Authority | Access Protocol | Key Verification Logic |
|----------|------------------------|------------------|--------------------------|
| **GSTN** | Goods & Services Tax Network / NIC | GSP/ASP channel, OAuth2 mTLS | Detect unfiled returns in the last 12 months; cross-verify taxable turnover vs. self-declared bid figures |
| **MCA21** | Ministry of Corporate Affairs | MCA21 V3 REST via API Setu / NDAP | Cross-bidder director (DIN) bipartite graph resolution; shell-company heuristic via company age vs. filed annual returns (MGT-7/AOC-4) |
| **CBDT/NSDL (PAN)** | Central Board of Direct Taxes / Protean eGov | Online PAN Verification (OPV), AES-256 + RSA | Levenshtein-distance name matching; alert if PAN is inoperative or name similarity < 85% |
| **Udyam/MSME** | Ministry of MSME | Udyam API via API Setu | Determine GFR Rule 153 exemption eligibility; flag expired/mismatched category |
| **CPPP / GeM Debarment** | CPPP / GeM | Automated batch query + webhook | Strict binary hard-eligibility failure on any active debarment order under GFR Rule 151 |

**Phased rollout schedule (as documented):**

| Milestone | Target Horizon | Deliverables |
|-----------|-----------------|---------------|
| Phase 1 — API Setu Onboarding | Q3 2026 | Register AuthBid on the API Setu gateway with government agency credentials |
| Phase 2 — GSTN & PAN Integration | Q4 2026 | Switch GST/PAN verification from mocks to GSP sandbox and NSDL production |
| Phase 3 — MCA21 & DIN Graph Ingestion | Q1 2027 | Integrate the live MCA21 V3 director master API for real-time corporate linkage resolution |
| Phase 4 — Full Production Certification | Q2 2027 | STQC security audit, CERT-In vulnerability certification, formal GeM production deployment |

---

## 22. Core Technical Differentiators / Unique Selling Points

- **Deterministic Rule Scrutiny** — hard eligibility checks and risk scores are computed mathematically, never hallucinated by an LLM, making every disqualification decision reproducible and legally defensible.
- **OSINT-style Graph Entity Resolution** — automatically detects cartel syndicates across shared directors, physical addresses, and banking channels, without requiring an officer to manually cross-reference documents.
- **Explainable 5-Component Risk Formula** — full transparency into exactly how much each of Consistency (30%), Collusion (25%), Financials (20%), Documents (15%), and Debarment (10%) contributed to a bidder's score.
- **Cryptographic Tamper-Evident SHA-256 Audit Chain** — a mathematically verifiable ledger with external RFC 3161-style Merkle anchoring, defending even against insider threats.
- **Role-Based Access Control** — distinct, enforced permissions for Officers, Committee Members, and System Admins.
- **Prompt-Injection Defense** — strict sanitization and structural isolation of any bidder-submitted text before it reaches the generative AI layer.
- **Document Vault with Inline Preview** — checksum-verified certificate preview without mandatory downloads.
- **Decision Safeguards** — mandatory justification modals and a visible, permanent audit log for every disqualification.

---

## 23. Limitations of the Current Prototype

For transparency in submission material, it is worth explicitly noting what is simulated vs. production-grade in the current build:

- The five statutory registries (GST, PAN, MCA21, Udyam, Blacklist) are **mock APIs backed by synthetic data**, not live government integrations — this is the explicit subject of the regulatory roadmap in Section 21.
- PostgreSQL, Neo4j, and Redis are provisioned in Docker Compose but the **application logic itself currently persists to in-memory Python data structures** (`models/database.py`), meaning data resets on backend restart in the current build; wiring the existing schemas into the already-provisioned databases is the natural next engineering step.
- The AI Copilot is wired directly to live Google Gemini 2.5 Flash via `langchain-google-genai` whenever `GEMINI_API_KEY` is configured in `.env`, automatically falling back to canonical deterministic intelligence when the key is absent or unreachable.
- CORS is fully open (`*`) and JWT/password-hashing libraries (`python-jose`, `passlib`) are included as dependencies but user authentication itself is not yet wired up beyond the header-based `X-User-Role` role selection — real login/session management is a pre-production requirement.
- Canonical dataset consistency is established: `synthetic_data.py`, AI Copilot responses, frontend defaults, and all project documentation reference identical bidder entities (TechVision, Reliable Computing, DigiCore, GreenTech, NexGen IT, Bharat Electronics, Quantum Digital, MegaByte, CloudFirst, Pinnacle Systems, ByteWave, Atlas Infosys) and tender estimated value (₹2.50 Cr / 25,000,000 INR).

None of these are unusual for a hackathon-stage prototype; they are noted here so that submission documentation accurately represents what is demonstrated live versus what is architected for production.

---

## 24. Future Scope

Building on the existing roadmap documents and architecture, natural extensions include:

- Full production wiring to GSTN, MCA21, CBDT/NSDL, Udyam, and CPPP live APIs per the phased rollout plan.
- Persisting verification results, audit chains, and officer decisions into the already-provisioned PostgreSQL and Neo4j instances (replacing the in-memory demo stores) for durability across restarts and multi-officer concurrent use.
- Wiring the live Gemini/LangGraph agent pipeline for fully dynamic (rather than templated) copilot narratives, while retaining the existing sanitization and disclaimer guardrails.
- Real user authentication/session management (leveraging the already-included `python-jose`/`passlib` dependencies) layered on top of the existing RBAC role model.
- Deeper graph analytics (e.g., true bipartite/community-detection algorithms via `networkx`, which is already a backend dependency) for subtler collusion patterns beyond exact-match director/address/bank overlap.
- OCR-based automated document data extraction (the `pdf2image`, `Pillow`, and `pyzbar` dependencies are present, suggesting planned document-upload ingestion rather than only synthetic pre-seeded profiles).
- Formal integration with the Competition Commission of India (CCI) referral workflow and the National Public Distributed Ledger anchoring channel described in the audit-anchoring roadmap.

---

## 25. Conclusion

AuthBid demonstrates a technically rigorous, legally-grounded approach to one of public procurement's hardest problems: catching sophisticated bid-rigging and cartel behavior that manual review routinely misses, while keeping every automated decision **explainable, reproducible, and cryptographically auditable**. Its architecture deliberately keeps generative AI in an assistive, sandboxed role and puts all decision-critical logic — eligibility checks, collusion detection, and risk scoring — in transparent, testable, deterministic code, backed by a genuinely tamper-evident audit trail. Combined with role-based governance and automated legal drafting grounded in specific statutory provisions (Competition Act 2002, GFR 2017), it presents a credible, extensible blueprint for how AI-assisted integrity tooling can be responsibly deployed inside a government procurement system like GeM.

---

*Document compiled from the full AuthBid-main source repository, covering the backend (FastAPI/Python), frontend (Next.js/React/TypeScript), test suite, Docker deployment configuration, and accompanying architecture documentation (`README.md`, `FEATURES.md`, `docs/AUDIT_ANCHORING.md`, `docs/REGULATORY_INTEGRATION_ROADMAP.md`, `CONTRIBUTING.md`).*
