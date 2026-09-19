# 🛡️ AuthBid — GeM Compliance Intelligence

> **AI-Powered Integrated Bid Compliance Verification & Collusion Detection Platform for GeM Procurement**  
> *Smart India Hackathon (SIH26100)*

---

## 📖 Quick Links
- **[Full Project Functionalities & Architecture (FEATURES.md)](./FEATURES.md)**
- **Frontend URL:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ⚡ Quick Start (Local Run)

### 1. Start Backend
```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start Frontend
```powershell
cd frontend
npm run dev
```

### 3. Or Run via Docker Compose
```bash
docker compose up -d
```

---

## 🏗️ System Architecture: Deterministic Rules vs. LLM Copilot

```mermaid
graph TD
    subgraph INGESTION["Input Data Ingestion"]
        Tender["GeM Tender RFP & Bids<br/>(GEM/2026/B/4521897)"]
        BidderDocs["Bidder Documents<br/>(GST REG-06, PAN, Balance Sheets)"]
    end

    subgraph DETERMINISTIC["Deterministic & Rule-Based Engines (Non-LLM / Mathematically Verifiable)"]
        direction TB
        RegEngine["<b>1. Regulatory Rules Engine</b><br/>• GSTN active filing check<br/>• CBDT PAN exact name matching<br/>• MCA21 incorporation & DIN scan<br/>• MSME Udyam GFR 153 exemption<br/>• CPPP / GeM Debarment check"]
        
        EntityRes["<b>2. Entity Resolution & Graph Engine</b><br/>• Common director DIN matching<br/>• Physical address string unification<br/>• Bank IFSC + account prefix linkage<br/>• Shell company age & filing heuristic"]
        
        RiskEngine["<b>3. 5-Vector Weighted Risk Scoring</b><br/>• Cross-Source Consistency (30%)<br/>• Collusion Indicators (25%)<br/>• Financial Health (20%)<br/>• Document Integrity (15%)<br/>• Blacklist Proximity (10%)"]
        
        AuditChain["<b>4. Cryptographic Audit Defense</b><br/>• SHA-256 block-by-block hash chaining<br/>• Merkle root commitment<br/>• External RFC 3161 timestamp anchoring<br/>• Tamper detection & broken block pinpointing"]
        
        LegalTemplates["<b>5. Statutory Legal Engine</b><br/>• Show Cause Notice drafting (GFR 151 / Competition Act 3(3))<br/>• Committee Scrutiny Memo generation"]
    end

    subgraph GENERATIVE["Generative AI Component (LLM-Backed)"]
        Copilot["<b>GeM Legal & Vigilance Copilot</b><br/>(Gemini 2.5 Flash)<br/>• Natural language bidder intelligence<br/>• Statutory cross-examination<br/>• <i>Protected by XML context isolation & input sanitization</i>"]
    end

    subgraph OUTPUTS["Outputs & Officer Actions"]
        Dash["Procurement Officer Dashboard"]
        CollusionGraph["Interactive Collusion Graph (2D)"]
        SCN["Formal Show Cause Notice"]
        DecisionLog["Immutable Decision Audit Log"]
    end

    Tender --> RegEngine
    BidderDocs --> RegEngine
    RegEngine --> EntityRes
    EntityRes --> RiskEngine
    RiskEngine --> AuditChain
    RiskEngine --> LegalTemplates

    AuditChain --> Dash
    EntityRes --> CollusionGraph
    LegalTemplates --> SCN
    RiskEngine --> Dash
    Dash --> DecisionLog

    RiskEngine -. Sanitized Context .-> Copilot
    Tender -. Sanitized Context .-> Copilot
    Copilot --> Dash

    classDef deterministic fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#1e3a8a;
    classDef generative fill:#fdf4ff,stroke:#c026d3,stroke-width:2px,stroke-dasharray: 5 5,color:#701a75;
    classDef inputs fill:#f8fafc,stroke:#64748b,stroke-width:1px,color:#0f172a;
    classDef outputs fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b;

    class RegEngine,EntityRes,RiskEngine,AuditChain,LegalTemplates deterministic;
    class Copilot generative;
    class Tender,BidderDocs inputs;
    class Dash,CollusionGraph,SCN,DecisionLog outputs;
```

---

## 🌟 Core Technical Differentiators
* **Deterministic Rule Scrutiny**: Hard eligibility checks and risk scores are computed mathematically, NOT hallucinated by an LLM.
* **OSINT Graph Entity Resolution**: Detects cartel syndicates (Ring 1 & Ring 2) across shared directors, physical addresses, and banking channels.
* **Explainable 5-Component Risk Formula**: Full transparency into Consistency (30%), Collusion (25%), Financials (20%), Documents (15%), and Debarment (10%).
* **Cryptographic Tamper-Evident SHA-256 Audit Chain**: Complete mathematical ledger with external RFC 3161 Merkle anchoring.
* **Role-Based Access Control (RBAC)**: Distinct permissions for Officers, Committee Members, and System Admins.
* **Prompt-Injection Defense**: Strictly sanitizes and isolates bidder document text in Copilot prompts.
* **Document Vault with Inline Preview**: Checksum-verified certificate preview without mandatory downloads.
* **Decision Safeguards**: Mandatory justification modals and visible audit logs for disqualifications.

---

## 🎯 Canonical Demonstration Scenario
* **Tender Reference:** `GEM/2026/B/4521897` (Supply of 500 Desktop Computers with 3-Year On-Site Warranty)
* **Estimated Value:** ₹2,50,00,000 (₹2.50 Crore / 25,000,000 INR)
* **Master Source of Truth:** [`backend/mock_apis/synthetic_data.py`](./backend/mock_apis/synthetic_data.py)
* **12 Synthetic Bidders:**
  1. `B001` — **TechVision Solutions Pvt. Ltd.** (₹2,35,00,000) — *Collusion Ring 1 (Leader)*
  2. `B002` — **Reliable Computing Systems Ltd.** (₹2,42,00,000) — *Clean Compliant Bidder*
  3. `B003` — **DigiCore Infosystems Pvt. Ltd.** (₹2,48,00,000) — *Collusion Ring 1 (Accomplice)*
  4. `B004` — **GreenTech Peripherals** (₹2,28,00,000) — *Expired MSME Certificate*
  5. `B005` — **NexGen IT Solutions Pvt. Ltd.** (₹2,39,00,000) — *Collusion Ring 2 (Shared PNB Bank & Phone)*
  6. `B006` — **Bharat Electronics & Computing** (₹2,45,00,000) — *PAN Name Typo (97% fuzzy match — passes)*
  7. `B007` — **Quantum Digital Services Pvt. Ltd.** (₹2,20,00,000) — *Collusion Ring 1 (Shell Entity Cover Bid)*
  8. `B008` — **MegaByte Computers Pvt. Ltd.** (₹2,40,00,000) — *Historical Debarment (Cleared)*
  9. `B009` — **CloudFirst Technologies Pvt. Ltd.** (₹2,32,00,000) — *Collusion Ring 2 (Shared PNB Bank & Phone)*
  10. `B010` — **Pinnacle Systems India Pvt. Ltd.** (₹2,48,00,000) — *Clean Compliant Bidder*
  11. `B011` — **ByteWave Electronics Pvt. Ltd.** (₹2,30,00,000) — *GST Filing Gaps (2 Quarters)*
  12. `B012` — **Atlas Infosys Solutions Pvt. Ltd.** (₹2,46,00,000) — *Clean Compliant Bidder*

---

## 💻 Tech Stack & Architecture Notes
* **Frontend:** Next.js 16 (App Router, Turbopack), React 19, TypeScript, TailwindCSS v4, Lucide-React, Recharts, React-Force-Graph-2D.
  * Single-page dashboard architecture (`app/page.tsx`) with internal view state tabs: **Dashboard**, **Bidders Dossier**, **Graph Analysis**, **Compliance Checklist**, **Audit Chain**, and **Scrutiny Report**. (Not separate `/graph` or `/audit` URL routes).
  * No Next Auth, Zod, or Server Actions dependencies are used.
* **Authentication & RBAC:** Role selection via `X-User-Role` header (`officer`, `committee_member`, `admin`) allowing seamless role switching for hackathon evaluation; production OAuth2/SSO authentication roadmap is detailed in [FEATURES.md](./FEATURES.md).
* **Backend:** FastAPI (Python 3.12), Pydantic v2, Uvicorn, NetworkX.
* **AI Copilot:** Powered by Google Gemini 2.5 Flash via `langchain-google-genai` when `GEMINI_API_KEY` is configured, with seamless automatic fallback to canonical deterministic rule responses.
* **Cryptographic Ledger:** SHA-256 block-by-block hash chaining with live tamper detection simulation and RFC 3161 Merkle anchoring.

---

For comprehensive architectural details and regulatory roadmaps, please refer to [FEATURES.md](./FEATURES.md), [docs/REGULATORY_INTEGRATION_ROADMAP.md](./docs/REGULATORY_INTEGRATION_ROADMAP.md), and [docs/AUDIT_ANCHORING.md](./docs/AUDIT_ANCHORING.md).

