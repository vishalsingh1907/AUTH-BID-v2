# Contributing to AuthBid

Thank you for your interest in contributing to **AuthBid (BidVerify)** — an AI-powered compliance verification and collusion detection platform for public procurement on the Government e-Marketplace (GeM).

---

## Code of Conduct

All contributors are expected to uphold a professional, inclusive, and collaborative environment. Respectful communication and constructive feedback are required.

---

## Getting Started

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ (with npm 10+)
- Docker & Docker Compose (optional for local full-stack containerization)

### 2. Local Backend Setup
```bash
cd backend
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
pip install pytest pytest-asyncio ruff

# Run backend development server:
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Local Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:3000`.

---

## Testing & Quality Assurance

All PRs must pass linting, type-checking, and test suites before merging:

### Backend Testing & Linting
```bash
# Run pytest suite:
python -m pytest backend/tests -v

# Run linter:
python -m ruff check backend/
```

### Frontend Type-Check & Linting
```bash
cd frontend
npx tsc --noEmit
npm run lint
```

---

## Branching & Commit Guidelines

1. **Branch Naming**:
   - `feat/feature-name` for new capabilities
   - `fix/bug-description` for fixes
   - `docs/documentation-update` for documentation changes
   - `test/test-enhancements` for testing additions

2. **Commit Messages**:
   Follow conventional commits:
   - `feat: add explainable risk breakdown component`
   - `fix: correct previous hash resolution in audit chain`
   - `docs: update regulatory roadmap for MCA21 V3`
   - `test: add unit test for shell company heuristic`

3. **Security**:
   - **NEVER** commit real API keys, secrets, or production database credentials.
   - Use `.env` for local secrets (gitignored).

---

## Pull Request Process

1. Fork or branch from `main`.
2. Ensure all automated tests pass locally (`pytest backend/tests/ -q`).
3. Open a Pull Request with a clear summary of changes, rationale, and screenshots for UI modifications.
4. Ensure GitHub Actions CI passes all checks.

---

## ⚠️ Canonical Data Source & Documentation Drift Prevention

> **Notice to Contributors on Historical Documentation Drift (Resolved):**  
> Earlier prototype iterations exhibited documentation and code drift where markdown documents described an illustrative bidder set (*Apex Infotech*, *Zenith Computech*, *InnoVision*) and an estimated tender value of ₹1.50 Cr, while the backend code executed a distinct 12-entity dataset with an estimated value of ₹2.50 Cr.  
>  
> This drift has been **strictly resolved and unified** across the entire repository:
>
> 1. **Single Source of Truth:**  
>    [`backend/mock_apis/synthetic_data.py`](file:///c:/Users/ASUS/Downloads/sih%202/backend/mock_apis/synthetic_data.py) is the sole canonical source of truth for all bidder names:
>    - `B001` TechVision Solutions Pvt. Ltd. (₹2,35,00,000)
>    - `B002` Reliable Computing Systems Ltd. (₹2,42,00,000)
>    - `B003` DigiCore Infosystems Pvt. Ltd. (₹2,48,00,000)
>    - `B004` GreenTech Peripherals (₹2,28,00,000)
>    - `B005` NexGen IT Solutions Pvt. Ltd. (₹2,39,00,000)
>    - `B006` Bharat Electronics & Computing (₹2,45,00,000)
>    - `B007` Quantum Digital Services Pvt. Ltd. (₹2,20,00,000)
>    - `B008` MegaByte Computers Pvt. Ltd. (₹2,40,00,000)
>    - `B009` CloudFirst Technologies Pvt. Ltd. (₹2,32,00,000)
>    - `B010` Pinnacle Systems India Pvt. Ltd. (₹2,48,00,000)
>    - `B011` ByteWave Electronics Pvt. Ltd. (₹2,30,00,000)
>    - `B012` Atlas Infosys Solutions Pvt. Ltd. (₹2,46,00,000)  
>    Tender value is canonically **₹2,50,00,000 (₹2.50 Cr / 25,000,000 INR)**.
>
> 2. **No Second Truth:**  
>    Contributors must never reintroduce divergent bidder names or values in documentation, Copilot canned responses, or frontend components.
>
> 3. **Copilot Honesty:**  
>    The AI Copilot (`/api/verification/copilot`) dynamically calls Google Gemini 2.5 Flash via `langchain-google-genai` when `GEMINI_API_KEY` is set in `.env`, and gracefully falls back to canonical rule-based vigilance responses when the key is absent.
>
> 4. **Route & Stack Honesty:**  
>    Graph Analysis and Audit Trail are interactive tabs/views within the single dashboard page (`app/page.tsx`), not separate Next.js routes. Frontend authentication is currently header-based (`X-User-Role`); do not add claims for Next Auth, Zod, or Server Actions unless they are genuinely installed and implemented.

