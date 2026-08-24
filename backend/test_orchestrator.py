import os
import sqlite3
from backend.orchestrator import DisputeOrchestrator

def seed_database():
    """Ensures ground truth orders table exists in SQLite."""
    conn = sqlite3.connect("represent_ai.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            amount REAL
        )
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO orders (order_id, customer_name, amount) 
        VALUES ('OD-1245789', 'Rahul Sharma', 12500.00)
    """)
    conn.commit()
    conn.close()

def run_pipeline_test():
    sample_image = "test.png"
    
    if not os.path.exists(sample_image):
        print(f"Error: Sample image not found at {sample_image}")
        return

    seed_database()

    print("=============================================================")
    print("  STARTING DYNAMIC END-TO-END PIPELINE (PHASES 1, 2 & 3)     ")
    print("=============================================================")
    
    orchestrator = DisputeOrchestrator()
    final_state = orchestrator.process_dispute(
        image_path=sample_image,
        ledger_customer_name="Rahul Sharma",
        ledger_amount=12500.00,
        generate_pdf=True
    )

    print("\n================ PIPELINE EXECUTION RESULTS ================")
    print(f"• Customer (Ledger ground truth): {final_state.ledger_customer_name}")
    print(f"• Customer (Extracted via OCR)  : {final_state.ocr_data.customer_name}")
    print(f"• Phase 1 Tamper Detected      : {final_state.metrics.ela_tamper_detected}")
    print(f"• ELA Pixel Variance           : {final_state.metrics.ela_max_variance}")
    print(f"• Phase 2 Verdict              : {final_state.auditor_output.get('authenticity_verdict')}")
    print(f"• Auditor Confidence Score     : {final_state.auditor_output.get('confidence_score')}")
    print(f"• Phase 3 PDF Path             : {final_state.pdf_path}")
    print("=============================================================\n")

if __name__ == "__main__":
    run_pipeline_test()