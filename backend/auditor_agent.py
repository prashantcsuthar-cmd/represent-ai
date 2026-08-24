import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from google import genai
from google.genai import types

from backend.state import OCRExtractedData, PreEvaluationMetrics, AuditResultData

load_dotenv()


# --- 1. Structured Output Schema for Phase 2 Auditor ---
class AuditorAnalysisOutput(BaseModel):
    authenticity_verdict: str = Field(
        description="VERIFIED, SUSPICIOUS, or REJECTED"
    )
    confidence_score: float = Field(
        description="Confidence score from 0.0 to 1.0"
    )
    key_findings: List[str] = Field(
        description="List of specific flags, supportive evidence, or observations"
    )
    mismatch_breakdown: str = Field(
        description="Detailed forensic summary explaining the evaluation results"
    )
    recommendation_for_defense: str = Field(
        description="Guidance for constructing the merchant defense brief in Phase 3"
    )


# --- 2. Prompt Construction Function ---
def build_auditor_prompt(
    ledger_customer_name: str,
    ledger_amount: float,
    ocr_data: OCRExtractedData,
    metrics: PreEvaluationMetrics
) -> str:
    """Formats Phase 1 deterministic metrics and OCR data into an Auditor Agent prompt."""
    
    prompt = f"""
You are an expert Forensic Financial Auditor and Chargeback Defense Investigation Agent.
Your goal is to evaluate customer dispute evidence by synthesizing ground-truth database records, OCR metadata, and forensic metrics.

### 1. GROUND TRUTH LEDGER DATA (Database)
- Expected Customer Name: {ledger_customer_name}
- Expected Amount: ${ledger_amount:.2f}

### 2. EXTRACTED OCR EVIDENCE DATA
- Customer Name on Proof: {ocr_data.customer_name}
- Order / Tracking ID: {ocr_data.order_id or ocr_data.tracking_number}
- Carrier Name: {ocr_data.carrier_name}
- Extracted Amount: {ocr_data.amount or 'Logistics POD (N/A)'}
- Delivery Status: {ocr_data.delivery_status}
- Order Date: {ocr_data.order_date}
- Delivery Date: {ocr_data.delivery_date}

### 3. PHASE 1 DETERMINISTIC & FORENSIC METRICS
- Name Similarity Score: {metrics.name_similarity_score} (Exact Match: {metrics.is_name_exact_match})
- ELA Statistical Variance: {metrics.ela_max_variance}
- Raw Forensic Flags: {metrics.forensic_flags}
- Tracking Format Valid: {metrics.tracking_format_valid}
- Date Timeline Valid: {metrics.timeline_valid}

### CRITICAL AUDITING DIRECTIVES:
1. **Contextual ELA Evaluation:** Note that raw digital mobile UI screenshots (such as BlueDart, Delhivery, or FedEx apps) naturally exhibit edge compression artifacts near crisp text headers, dark mode borders, and digital signature boxes. Evaluate if variance represents mobile interface rendering rather than fraudulent document manipulation.
2. **Logistics vs Invoice Discrepancies:** Courier proof-of-delivery screens confirm physical fulfillment (status DELIVERED, OTP codes, signatures) and standardly omit transaction amounts. Do not flag authentic logistics screens as fraudulent solely due to an absent order value field.
3. **Verdict Determination:** Synthesize all indicators. If customer name matches ground truth (similarity >= 0.85) and fulfillment confirmation is present, classify the document as VERIFIED with high confidence, explaining any UI edge artifacts in your breakdown.
"""
    return prompt.strip()


# --- 3. Main Auditor Agent Execution Function ---
def run_auditor_agent(
    ledger_customer_name: str,
    ledger_amount: float,
    ocr_data: OCRExtractedData,
    metrics: PreEvaluationMetrics,
    api_key: Optional[str] = None
) -> AuditorAnalysisOutput:
    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")

    if not effective_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    client = genai.Client(api_key=effective_api_key)
    
    prompt = build_auditor_prompt(
        ledger_customer_name=ledger_customer_name,
        ledger_amount=ledger_amount,
        ocr_data=ocr_data,
        metrics=metrics
    )

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AuditorAnalysisOutput,
            temperature=0.1,
        ),
    )

    result_dict = json.loads(response.text)
    return AuditorAnalysisOutput(**result_dict)


# --- 4. Stateful Pipeline Wrapper for main.py ---
def run_auditor_agent_stateful(state):
    """
    Stateful wrapper expected by main.py to handle DisputeState integration directly.
    """
    ocr_data = getattr(state, "ocr_data", OCRExtractedData())
    metrics = getattr(state, "metrics", PreEvaluationMetrics())
    
    ledger_name = getattr(state, "ledger_customer_name", "") or getattr(state, "customer_name", "")
    ledger_amt = getattr(state, "ledger_amount", 0.0) or getattr(state, "amount", 0.0)

    try:
        raw_output = run_auditor_agent(
            ledger_customer_name=ledger_name,
            ledger_amount=ledger_amt,
            ocr_data=ocr_data,
            metrics=metrics
        )
        
        state.audit_data = AuditResultData(
            compliance_score=raw_output.confidence_score * 100.0,
            recommended_action=raw_output.authenticity_verdict,
            final_pack_summary=raw_output.mismatch_breakdown,
            reasoning_trace=raw_output.key_findings,
            email_draft=raw_output.recommendation_for_defense,
            ce30_match=metrics.amount_match
        )
        state.is_ready_for_submission = raw_output.authenticity_verdict == "VERIFIED"
        state.requires_human_review = raw_output.authenticity_verdict == "SUSPICIOUS"
    except Exception as e:
        state.audit_data = AuditResultData(
            compliance_score=0.0,
            recommended_action="REVIEW",
            final_pack_summary=f"Audit execution error: {str(e)}",
            reasoning_trace=["Pipeline fallback triggered due to exception."]
        )
        state.requires_human_review = True
        
    return state