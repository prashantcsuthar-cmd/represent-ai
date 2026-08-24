from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# --- Pydantic Data Models ---

class OCRExtractedData(BaseModel):
    customer_name: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[str] = None
    carrier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    delivery_status: Optional[str] = None
    order_date: Optional[str] = None
    delivery_date: Optional[str] = None
    transaction_amount: Optional[float] = None
    status: Optional[str] = None
    otp_verified: Optional[bool] = None
    has_signature: Optional[bool] = None
    raw_ocr_text: Optional[str] = ""

class PreEvaluationMetrics(BaseModel):
    name_similarity_score: float = 0.0
    is_name_exact_match: bool = False
    ela_max_variance: float = 0.0
    ela_avg_variance: float = 0.0
    ela_tamper_detected: bool = False
    forensic_flags: List[str] = Field(default_factory=list)
    tracking_format_valid: bool = False
    delivery_timeline_valid: bool = False
    timeline_valid: bool = False
    amount_matched: bool = False
    amount_match: bool = False

class AuditResultData(BaseModel):
    compliance_score: float = 0.0
    recommended_action: str = "REVIEW"
    final_pack_summary: str = ""
    reasoning_trace: List[str] = Field(default_factory=list)
    email_draft: str = ""
    ce30_match: bool = False

@dataclass
class ForensicMetrics:
    name_similarity_score: float = 0.0
    ela_max_variance: float = 0.0
    ela_avg_variance: float = 0.0
    tracking_format_valid: bool = False
    delivery_timeline_valid: bool = False
    amount_matched: bool = False

# --- Pipeline State ---

@dataclass
class PipelineState:
    file_path: str = ""
    dispute_id: str = ""
    merchant_id: str = "MERCH-4091"
    amount: float = 0.0
    customer_name: str = ""
    ledger_customer_name: str = ""
    ledger_amount: float = 0.0
    file_bytes_base64: str = ""
    mime_type: str = ""
    extracted_ocr_text: str = ""
    ocr_data: OCRExtractedData = field(default_factory=OCRExtractedData)
    metrics: PreEvaluationMetrics = field(default_factory=PreEvaluationMetrics)
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    auditor_output: Dict[str, Any] = field(default_factory=dict)
    audit_data: Optional[AuditResultData] = None
    is_tampered: bool = False
    fallback_flags: List[str] = field(default_factory=list)
    is_ready_for_submission: bool = False
    requires_human_review: bool = False
    pdf_path: str = ""

    def __post_init__(self):
        if self.customer_name and not self.ledger_customer_name:
            self.ledger_customer_name = self.customer_name
        if self.amount and not self.ledger_amount:
            self.ledger_amount = self.amount

# Alias for compatibility across backend imports
DisputeState = PipelineState