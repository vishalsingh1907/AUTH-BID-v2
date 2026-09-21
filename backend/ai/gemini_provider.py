"""
SIH26100 — Google Gemini 2.5 Flash Analysis Provider
Executes governed model-assisted evidence review with structured JSON output and schema validation.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json
import os
from config import settings
from ai.governance import ModelReviewResponse, ObservedFact, PromptSanitizer


class GeminiAnalysisProvider:
    name: str = "Google Gemini Provider"
    version: str = "gemini-flash-lite-latest"

    async def review_evidence(
        self,
        tender_id: str,
        bidder_id: str,
        query: str,
        sanitized_context: str,
        evidence_items: List[Dict[str, Any]],
    ) -> Optional[ModelReviewResponse]:
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        if not api_key or not api_key.strip() or api_key.strip() in ["your_gemini_api_key_here", ""]:
            return None

        start_time = datetime.now()
        input_content = f"{tender_id}|{bidder_id}|{query}|{sanitized_context}"
        input_hash = hashlib.sha256(input_content.encode()).hexdigest()

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage

            active_model = settings.LLM_MODEL or "gemini-flash-lite-latest"
            if "2.5" in active_model or "2.0" in active_model or "1.5" in active_model:
                active_model = "gemini-flash-lite-latest"

            llm = ChatGoogleGenerativeAI(
                model=active_model,
                google_api_key=api_key.strip(),
                temperature=0.1,
                request_timeout=15,
                max_retries=1,
            )

            system_instruction = (
                "You are an officer-supervised procurement intelligence assistant for the Government e-Marketplace (GeM).\n"
                "Your role is strictly ASSISTIVE. You summarize evidence, explain potential relationships, and suggest follow-up questions.\n"
                "You do NOT make legal disqualification decisions; the Procurement Officer is the sole decision-maker.\n\n"
                "Respond ONLY with valid JSON matching this schema:\n"
                "{\n"
                '  "summary": "<Objective summary grounded in evidence>",\n'
                '  "observed_facts": [\n'
                '    {"statement": "<Fact statement>", "evidence_ids": ["<EVID-ID>"], "source": "<Source System>"}\n'
                "  ],\n"
                '  "uncertainties": ["<Missing data or connector limitations>"],\n'
                '  "suggested_follow_up": ["<Question or verification step for officer>"],\n'
                '  "officer_decision_required": true,\n'
                '  "disclaimer": "Model-assisted analysis; officer review required."\n'
                "}\n"
                "Do NOT wrap in markdown fences. Output strictly valid JSON."
            )

            user_prompt = (
                f"Tender ID: {tender_id}\n"
                f"Bidder ID: {bidder_id or 'All Bidders'}\n"
                f"Query: {query}\n"
                f"Context: {sanitized_context}\n"
                f"Evidence Items: {json.dumps(evidence_items[:8], default=str)}"
            )

            response = await llm.ainvoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=user_prompt),
            ])

            raw_content = response.content
            if isinstance(raw_content, list):
                raw_text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content).strip()
            else:
                raw_text = str(raw_content).strip()

            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed = json.loads(raw_text)
            output_hash = hashlib.sha256(raw_text.encode()).hexdigest()
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            facts = [
                ObservedFact(
                    statement=f.get("statement", ""),
                    evidence_ids=f.get("evidence_ids", []),
                    source=f.get("source", "Connector Evidence"),
                )
                for f in parsed.get("observed_facts", [])
            ]

            return ModelReviewResponse(
                summary=parsed.get("summary", ""),
                observed_facts=facts,
                uncertainties=parsed.get("uncertainties", []),
                suggested_follow_up=parsed.get("suggested_follow_up", []),
                officer_decision_required=True,
                disclaimer=f"Model-assisted analysis ({active_model}); officer review required.",
                provider="google_gemini",
                model_name=active_model,
                prompt_template_version="v2.0",
                input_hash=input_hash,
                output_hash=output_hash,
                latency_ms=latency_ms,
                validation_status="valid",
            )
        except Exception:
            return None
