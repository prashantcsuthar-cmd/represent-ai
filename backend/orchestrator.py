import logging
from typing import Dict, Any, Optional
from backend.state import AuditState, GateDecision
from backend.pre_evaluator import run_pre_evaluation
from backend.auditor_agent import run_gemini_synthesis
from backend.ocr_engine import extract_document_entities_safe
from backend.pdf_generator import generate_defense_brief_pdf

logger = logging.getLogger("orchestrator")

def calculate_reliability_score(state: AuditState) -> float:
    m = state.metrics
    if not m:
        return 0.0
    
    score = (
        (m.name_similarity_score * 0.35) +
        (0.25 if m.tracking_format_valid else 0.0) +
        (0.20 if m.delivery_status_valid else 0.0) +
        (0.10 if m.amount_match else 0.0) +
        (0.10 if not m.ela_localized_tampering_detected else 0.0)
    )
    return round(score * 100, 2)

def process_dispute_pipeline(state: AuditState) -> AuditState:
    logger.info(f"Starting pipeline execution for Case ID: {state.case_id}")
    
    # 0. Run OCR/Text extraction if file is provided and fields are empty
    if state.image_path and not state.extracted_name:
        extracted = extract_document_entities_safe(state.image_path)
        state.extracted_name = extracted.get("extracted_name")
        state.extracted_amount = extracted.get("extracted_amount")
        state.extracted_tracking_id = extracted.get("extracted_tracking_id")
        state.extracted_status = extracted.get("extracted_status")

    # Phase 1: Pre-Evaluation & Forensics
    metrics = run_pre_evaluation(state)
    state.metrics = metrics
    
    # Phase 2: Unyielding Deterministic & Tampering Gate
    if metrics.hard_contradiction_triggered or metrics.ela_localized_tampering_detected:
        state.gate_decision = GateDecision.HARD_FAIL
        state.evidence_reliability_score = calculate_reliability_score(state)
        state.human_review_required = False
        
        reasons = list(metrics.contradiction_reasons)
        if metrics.ela_localized_tampering_detected and "Localized Compression Anomaly (Image Tampering Detected)" not in reasons:
            reasons.append("Localized Compression Anomaly (Image Tampering Detected)")

        state.audit_log.append({
            "stage": "Deterministic Gate",
            "action": "AUTO_REJECT",
            "reasons": reasons
        })
        
        state.llm_synthesis = (
            f"AUTOMATED REJECTION: Hard contradictions or image tampering found in evidence fields. "
            f"Reasons: {', '.join(reasons)}"
        )
        
        try:
            state.pdf_path = generate_defense_brief_pdf(state)
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")

        return state

    # Calculate Reliability Score
    reliability = calculate_reliability_score(state)
    state.evidence_reliability_score = reliability

    # Phase 3: HITL Escalation Routing
    if reliability < 75.0:
        state.gate_decision = GateDecision.AMBIGUOUS
        state.human_review_required = True
        state.audit_log.append({
            "stage": "Reliability Evaluator",
            "action": "ROUTE_TO_HITL",
            "score": reliability,
            "reasons": metrics.contradiction_reasons
        })
    else:
        state.gate_decision = GateDecision.CLEAN
        state.human_review_required = False
        state.audit_log.append({
            "stage": "Reliability Evaluator",
            "action": "PASS_CLEAN",
            "score": reliability
        })

    # Phase 4: Gemini LLM Synthesis
    try:
        synthesis_result = run_gemini_synthesis(state)
        state.llm_synthesis = synthesis_result
    except Exception as e:
        logger.error(f"Error during Gemini synthesis for Case {state.case_id}: {str(e)}")
        state.llm_synthesis = "SYNTHESIS WARNING: Synthesis incomplete due to API issue. Fallback to forensic metrics."

    try:
        state.pdf_path = generate_defense_brief_pdf(state)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    return state


class DisputeOrchestrator:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def run_pipeline(self, state: AuditState) -> AuditState:
        return process_dispute_pipeline(state)

    def process(self, state: AuditState) -> AuditState:
        return process_dispute_pipeline(state)

    def process_dispute(
        self,
        state: Optional[AuditState] = None,
        case_id: str = "CASE-TEST-001",
        file_path: Optional[str] = None,
        image_path: Optional[str] = None,
        ledger_customer_name: str = "Prashanth C",
        ledger_amount: float = 150.0,
        ledger_tracking_id: str = "TRK123456",
        extracted_name: Optional[str] = None,
        extracted_amount: Optional[float] = None,
        extracted_tracking_id: Optional[str] = None,
        extracted_status: Optional[str] = None,
        generate_pdf: bool = True,
        **kwargs
    ) -> AuditState:
        actual_path = file_path or image_path or kwargs.get("image_path")
        if state is None:
            c_name = kwargs.get("customer_name", ledger_customer_name)
            c_amt = kwargs.get("amount", ledger_amount)
            c_trk = kwargs.get("tracking_id", ledger_tracking_id)
            
            state = AuditState(
                case_id=kwargs.get("dispute_id", case_id),
                image_path=actual_path,
                expected_customer_name=c_name,
                expected_amount=c_amt,
                expected_tracking_id=c_trk,
                extracted_name=extracted_name,
                extracted_amount=extracted_amount,
                extracted_tracking_id=extracted_tracking_id,
                extracted_status=extracted_status
            )
        else:
            if actual_path:
                state.image_path = actual_path
        
        return process_dispute_pipeline(state)