from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class GateDecision(str, Enum):
    HARD_FAIL = "HARD_FAIL"
    AMBIGUOUS = "AMBIGUOUS"
    CLEAN = "CLEAN"

class PreEvaluatorMetrics(BaseModel):
    name_similarity_score: float = Field(..., ge=0.0, le=1.0)
    amount_match: bool
    tracking_format_valid: bool
    delivery_status_valid: bool
    ela_max_variance: float
    ela_localized_tampering_detected: bool
    hard_contradiction_triggered: bool
    contradiction_reasons: List[str] = Field(default_factory=list)

    @property
    def ela_tamper_detected(self) -> bool:
        return self.ela_localized_tampering_detected

    @property
    def ela_variance(self) -> float:
        return self.ela_max_variance

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in PreEvaluatorMetrics")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class OCRExtractedData(BaseModel):
    customer_name: Optional[str] = None
    extracted_name: Optional[str] = None
    amount: Optional[float] = None
    extracted_amount: Optional[float] = None
    tracking_id: Optional[str] = None
    extracted_tracking_id: Optional[str] = None
    delivery_status: Optional[str] = None
    extracted_status: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in OCRExtractedData")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

class AuditState(BaseModel):
    case_id: str
    image_path: Optional[str] = None
    pdf_path: Optional[str] = None
    raw_text: Optional[str] = None
    
    expected_customer_name: str
    expected_amount: float
    expected_tracking_id: str
    
    extracted_name: Optional[str] = None
    extracted_amount: Optional[float] = None
    extracted_tracking_id: Optional[str] = None
    extracted_status: Optional[str] = None
    
    metrics: Optional[PreEvaluatorMetrics] = None
    gate_decision: GateDecision = GateDecision.AMBIGUOUS
    
    llm_synthesis: Optional[str] = None
    evidence_reliability_score: float = 0.0
    human_review_required: bool = False
    audit_log: List[Dict[str, Any]] = Field(default_factory=list)

    @property
    def ledger_customer_name(self) -> str:
        return self.expected_customer_name

    @property
    def ledger_amount(self) -> float:
        return self.expected_amount

    @property
    def ledger_tracking_id(self) -> str:
        return self.expected_tracking_id

    @property
    def ocr_data(self) -> OCRExtractedData:
        return OCRExtractedData(
            customer_name=self.extracted_name,
            extracted_name=self.extracted_name,
            amount=self.extracted_amount,
            extracted_amount=self.extracted_amount,
            tracking_id=self.extracted_tracking_id,
            extracted_tracking_id=self.extracted_tracking_id,
            delivery_status=self.extracted_status,
            extracted_status=self.extracted_status
        )

    @property
    def auditor_output(self) -> Dict[str, Any]:
        return {
            "authenticity_verdict": self.gate_decision.value,
            "confidence_score": self.evidence_reliability_score,
            "synthesis": self.llm_synthesis or "",
            "human_review_required": self.human_review_required,
            "reasons": self.metrics.contradiction_reasons if self.metrics else []
        }

DisputeState = AuditState
PreEvaluationMetrics = PreEvaluatorMetrics

class AuditResultData(BaseModel):
    gate_decision: GateDecision
    reliability_score: float
    synthesis: Optional[str] = None