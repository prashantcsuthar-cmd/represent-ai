from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.state import AuditState, OCRExtractedData, PreEvaluationMetrics, GateDecision
from backend.pre_evaluator import validate_tracking_format, validate_delivery_status, calculate_name_similarity


class AuditorAnalysisOutput(BaseModel):
    authenticity_verdict: str = Field(description="ACCEPTED or REJECTED")
    confidence_score: float = Field(description="Confidence score calculated from evidence")
    key_findings: List[str] = Field(description="List of specific flags or observations")
    mismatch_breakdown: str = Field(description="Detailed forensic summary explaining results")
    recommendation_for_defense: str = Field(description="Guidance for constructing defense brief")


def run_gemini_synthesis(state: AuditState) -> str:
    m = state.metrics
    findings = []
    if m:
        if m.hard_contradiction_triggered:
            findings.append(f"Contradictions detected: {', '.join(m.contradiction_reasons)}")
        if m.ela_localized_tampering_detected:
            findings.append("Localized ELA compression anomaly detected in proof image.")
        if m.name_similarity_score < 0.70:
            findings.append(f"Name similarity low ({m.name_similarity_score * 100:.1f}%).")
        if not m.amount_match:
            findings.append("Extracted amount does not match ledger amount.")

    summary = (
        f"AUDIT SUMMARY [Case {state.case_id}]:\n"
        f"- Gate Decision: {state.gate_decision.value if hasattr(state.gate_decision, 'value') else state.gate_decision}\n"
        f"- Evidence Reliability Score: {state.evidence_reliability_score}%\n"
        f"- Escalation Status: {'Flagged for HITL Review' if state.human_review_required else 'Automated Routing Completed'}\n"
        f"- Key Observations: {'; '.join(findings) if findings else 'All evidence fields validated successfully.'}"
    )
    return summary


def run_auditor_agent_offline(
    ledger_customer_name: str,
    ledger_amount: float,
    ocr_data: OCRExtractedData,
    metrics: PreEvaluationMetrics,
    ablation_config: dict = None
) -> AuditorAnalysisOutput:
    config = ablation_config or {"use_ela": True, "use_fuzzy": True, "use_tracking_val": True}
    flags = []

    # ENFORCED STRICT DETERMINISTIC GATE: Hard contradictions take unconditional precedence
    if metrics.hard_contradiction_triggered:
        flags.extend(metrics.contradiction_reasons)

    # Additional explicit deterministic constraint evaluations
    if not metrics.delivery_status_valid:
        msg = f"Non-delivered fulfillment status: '{ocr_data.get('extracted_status') or 'MISSING'}'"
        if msg not in flags:
            flags.append(msg)

    if config.get("use_tracking_val", True) and not metrics.tracking_format_valid:
        msg = f"Malformed or unverified tracking ID format: '{ocr_data.get('extracted_tracking_id')}'"
        if msg not in flags:
            flags.append(msg)

    ela_var = metrics.ela_max_variance
    ela_tamp = metrics.ela_localized_tampering_detected
    if config.get("use_ela", True) and (ela_var > 75.0 or ela_tamp):
        msg = f"High ELA error variance detected: {ela_var:.1f}"
        if msg not in flags:
            flags.append(msg)

    effective_name_score = metrics.name_similarity_score if config.get("use_fuzzy", True) else (1.0 if metrics.name_similarity_score == 1.0 else 0.0)
    if effective_name_score < 0.70:
        msg = f"Recipient name similarity below threshold: {effective_name_score:.2f}"
        if msg not in flags:
            flags.append(msg)

    ext_amt = ocr_data.get('extracted_amount')
    if ext_amt is not None and not metrics.amount_match:
        msg = f"Amount mismatch: Extracted ${ext_amt:.2f} vs Ledger ${ledger_amount:.2f}"
        if msg not in flags:
            flags.append(msg)

    # Unconditional hard rule block: If any contradiction or flag is present, verdict is strictly REJECTED
    is_verified = (len(flags) == 0 and not metrics.hard_contradiction_triggered)
    rule_score = 0.95 if is_verified else 0.15

    if is_verified:
        return AuditorAnalysisOutput(
            authenticity_verdict="ACCEPTED",
            confidence_score=rule_score,
            key_findings=["POD verified", "Identity matched", "Fulfillment status confirmed", "Amount matched"],
            mismatch_breakdown="Evidence details fully align with ground-truth ledger data.",
            recommendation_for_defense="Submit official chargeback defense with verified proof of delivery."
        )
    else:
        recommendation = f"Dispute rejected due to validation failures: {', '.join(flags)}."
        return AuditorAnalysisOutput(
            authenticity_verdict="REJECTED",
            confidence_score=rule_score,
            key_findings=flags,
            mismatch_breakdown="; ".join(flags),
            recommendation_for_defense=recommendation
        )


def audit_dispute(payload_or_state: Any, offline_mode: bool = True, ablation_config: dict = None) -> Dict[str, Any]:
    if isinstance(payload_or_state, dict):
        ledger_name = payload_or_state.get("ledger_customer_name", "")
        ledger_amount = float(payload_or_state.get("ledger_amount", 0.0))
        
        extracted_name = payload_or_state.get("extracted_name", ledger_name)
        extracted_amount = payload_or_state.get("extracted_amount", ledger_amount)
        tracking_id = payload_or_state.get("extracted_tracking_id") or payload_or_state.get("tracking_id", "")
        status = payload_or_state.get("extracted_status") or payload_or_state.get("delivery_status", "")

        raw_text = payload_or_state.get("raw_text", "")
        if raw_text:
            for line in raw_text.split("\n"):
                if "Tracking ID:" in line and not tracking_id:
                    tracking_id = line.split("Tracking ID:")[1].strip()
                elif "Status:" in line and not status:
                    status = line.split("Status:")[1].strip()

        ela_var = float(payload_or_state.get("ela_max_variance", 0.0))
        ela_tamper = bool(payload_or_state.get("ela_tamper_detected", False))

        ocr_data = OCRExtractedData(
            extracted_name=extracted_name,
            extracted_amount=extracted_amount,
            extracted_tracking_id=tracking_id,
            extracted_status=status
        )

        metrics = PreEvaluationMetrics(
            name_similarity_score=calculate_name_similarity(extracted_name, ledger_name),
            amount_match=(extracted_amount == ledger_amount) if extracted_amount is not None else True,
            tracking_format_valid=validate_tracking_format(tracking_id),
            delivery_status_valid=validate_delivery_status(status),
            ela_max_variance=ela_var,
            ela_localized_tampering_detected=ela_tamper,
            hard_contradiction_triggered=False,
            contradiction_reasons=[]
        )

        analysis = run_auditor_agent_offline(ledger_name, ledger_amount, ocr_data, metrics, ablation_config)
        verdict = analysis.authenticity_verdict

        return {
            "verdict": verdict,
            "authenticity_verdict": verdict,
            "confidence_score": analysis.confidence_score,
            "key_findings": analysis.key_findings,
            "mismatch_breakdown": analysis.mismatch_breakdown,
            "recommendation_for_defense": analysis.recommendation_for_defense
        }

    elif hasattr(payload_or_state, "extracted_name"):
        state = payload_or_state
        ocr_data = OCRExtractedData(
            extracted_name=state.extracted_name,
            extracted_amount=state.extracted_amount,
            extracted_tracking_id=state.extracted_tracking_id,
            extracted_status=state.extracted_status
        )
        analysis = run_auditor_agent_offline(state.expected_customer_name, state.expected_amount, ocr_data, state.metrics, ablation_config)
        verdict = analysis.authenticity_verdict

        return {
            "verdict": verdict,
            "authenticity_verdict": verdict,
            "confidence_score": analysis.confidence_score,
            "key_findings": analysis.key_findings,
            "mismatch_breakdown": analysis.mismatch_breakdown,
            "recommendation_for_defense": analysis.recommendation_for_defense
        }

    raise ValueError("Invalid payload passed to audit_dispute")


def run_auditor_agent_stateful(state: AuditState, offline_mode: bool = True, ablation_config: dict = None) -> AuditState:
    ocr_data = OCRExtractedData(
        extracted_name=state.extracted_name,
        extracted_amount=state.extracted_amount,
        extracted_tracking_id=state.extracted_tracking_id,
        extracted_status=state.extracted_status
    )
    metrics = state.metrics
    ledger_name = state.expected_customer_name
    ledger_amt = state.expected_amount

    raw_output = run_auditor_agent_offline(ledger_name, ledger_amt, ocr_data, metrics, ablation_config)

    state.llm_synthesis = raw_output.mismatch_breakdown
    state.evidence_reliability_score = round(raw_output.confidence_score * 100.0, 2)
    state.human_review_required = (raw_output.authenticity_verdict in ["SUSPICIOUS", "REVIEW"])
    
    # Enforce unconditional gate decision state mapping
    if raw_output.authenticity_verdict == "REJECTED":
        state.gate_decision = GateDecision.HARD_FAIL
    else:
        state.gate_decision = GateDecision.CLEAN

    return state