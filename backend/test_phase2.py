from backend.state import OCRExtractedData
from backend.pre_evaluator import execute_phase1_preeval
from backend.auditor_agent import run_auditor_agent

def run_phase2_test():
    # 1. Ground Truth
    ledger_customer_name = "Rahul Sharma"
    ledger_amount = 1250.00

    # 2. Tampered OCR Data Simulation
    mock_ocr_data = OCRExtractedData(
        customer_name="John Fake Person",
        order_id="ORD-1001",
        amount="$1250.00",
        tracking_number="AWB9876543210",
        carrier_name="Delhivery",
        delivery_status="Delivered",
        order_date="2026-08-10",
        delivery_date="2026-08-12"
    )

    # 3. Read image bytes
    with open("test.png", "rb") as f:
        file_bytes = f.read()

    # 4. Phase 1 Pre-Eval
    print("--- Executing Phase 1 ---")
    p1_metrics = execute_phase1_preeval(
        ledger_customer_name=ledger_customer_name,
        ledger_amount=ledger_amount,
        ocr_data=mock_ocr_data,
        file_bytes=file_bytes,
        mime_type="image/png"
    )

    # 5. Phase 2 Auditor Agent
    print("--- Executing Phase 2 Auditor Agent ---")
    audit_result = run_auditor_agent(
        ledger_customer_name=ledger_customer_name,
        ledger_amount=ledger_amount,
        ocr_data=mock_ocr_data,
        metrics=p1_metrics
    )

    # 6. Display Phase 2 Audit Output
    print("\nPhase 2 Auditor Output:")
    print(f"• Verdict: {audit_result.authenticity_verdict}")
    print(f"• Confidence Score: {audit_result.confidence_score}")
    print(f"• Key Findings: {audit_result.key_findings}")
    print(f"• Mismatch Breakdown: {audit_result.mismatch_breakdown}")

if __name__ == "__main__":
    run_phase2_test()