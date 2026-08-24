from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from backend.state import DisputeState
from backend.auditor_agent import run_auditor_agent_stateful

load_dotenv()

app = FastAPI(title="Represent AI Engine")

class DisputeRequest(BaseModel):
    dispute_id: str
    merchant_id: str = "MERCH-4091"
    amount: float
    customer_name: str
    file_bytes_base64: str
    mime_type: str

@app.post("/run-pipeline")
async def run_pipeline(req: DisputeRequest):
    try:
        # Initialize DisputeState
        initial_state = DisputeState(
            dispute_id=req.dispute_id,
            merchant_id=req.merchant_id,
            amount=req.amount,
            customer_name=req.customer_name,
            file_bytes_base64=req.file_bytes_base64,
            mime_type=req.mime_type
        )
        
        # Execute Graph Node Pipeline
        final_state = run_auditor_agent_stateful(initial_state)
        
        # Transform response for Streamlit compatibility
        return {
            "compliance_score": final_state.audit_data.compliance_score if final_state.audit_data else 0,
            "recommended_action": final_state.audit_data.recommended_action if final_state.audit_data else "REVIEW",
            "final_pack_summary": final_state.audit_data.final_pack_summary if final_state.audit_data else "",
            "reasoning_trace": final_state.audit_data.reasoning_trace if final_state.audit_data else [],
            "email_draft": final_state.audit_data.email_draft if final_state.audit_data else "",
            "is_tampered": final_state.is_tampered,
            "fallback_flags": final_state.fallback_flags,
            "is_ready_for_submission": final_state.is_ready_for_submission,
            "requires_human_review": final_state.requires_human_review,
            "ce30_match": final_state.audit_data.ce30_match if final_state.audit_data else False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))