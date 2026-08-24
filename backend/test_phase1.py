import os
import sqlite3
import mimetypes
from backend.ocr_engine import extract_document_entities_safe
from backend.pre_evaluator import execute_phase1_preeval

def seed_database():
    """Ensures the orders table exists and contains ground-truth records."""
    db_path = "represent_ai.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create orders table if it doesn't exist yet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            amount REAL
        )
    """)
    
    # Seed test order OD-1245789 matching the image order ID
    cursor.execute("""
        INSERT OR REPLACE INTO orders (order_id, customer_name, amount) 
        VALUES ('OD-1245789', 'Rahul Sharma', 12500.00)
    """)
    
    conn.commit()
    conn.close()

def get_ledger_order(order_id: str):
    """Fetches ground truth customer name and amount directly from SQLite."""
    conn = sqlite3.connect("represent_ai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT customer_name, amount FROM orders WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"customer_name": row[0], "amount": float(row[1])}
    return {"customer_name": None, "amount": 0.0}

def run_dynamic_test(image_path: str, default_order_id: str = "ORD-1001"):
    print(f"\n--- Running Fully Dynamic Phase 1 Test on: {image_path} ---")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found.")
        return

    # Read image bytes and infer MIME type for extract_document_entities_safe
    with open(image_path, "rb") as f:
        file_bytes = f.read()
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/png"

    # 1. Dynamically extract text using OCR Engine
    print("1. Executing OCR engine...")
    ocr_data = extract_document_entities_safe(file_bytes, mime_type)
    print(f"   • Extracted Name: {ocr_data.customer_name}")
    print(f"   • Extracted Order ID: {ocr_data.order_id}")
    print(f"   • Extracted Amount: {ocr_data.amount}")
    print(f"   • Extracted Tracking #: {ocr_data.tracking_number}")
    
    # Fallback to default_order_id if OCR returned Null or empty
    target_order_id = ocr_data.order_id if ocr_data.order_id and ocr_data.order_id != "Null" else default_order_id
    
    # 2. Query SQL Database dynamically
    print(f"2. Querying database for Order ID '{target_order_id}'...")
    ledger_record = get_ledger_order(target_order_id)
    print(f"   • Database Ground Truth Name: {ledger_record['customer_name']}")
    print(f"   • Database Ground Truth Amount: {ledger_record['amount']}")
    
    # 3. Perform pre-evaluation on real dynamic data
    print("3. Executing Forensic Pre-Evaluator...")
    results = execute_phase1_preeval(
        image_path=image_path,
        ocr_data=ocr_data,
        ledger_name=ledger_record["customer_name"],
        ledger_amount=ledger_record["amount"]
    )

    print("\n==========================================")
    print("DYNAMIC PHASE 1 EVALUATION RESULTS:")
    print("==========================================")
    print(f"• Name Similarity Score: {results['name_similarity']:.4f} (Exact Match: {results['is_exact_name_match']})")
    print(f"• ELA Max Variance: {results['ela_variance']:.2f}")
    print(f"• Tamper Detected: {results['tamper_detected']}")
    print(f"• Forensic Flags Raised: {results['forensic_flags']}")
    print(f"• Amount Match: {results['amount_match']}")
    print(f"• Tracking Format Valid: {results['tracking_format_valid']}")
    print("==========================================\n")

if __name__ == "__main__":
    # Ensure database table and test record are seeded before running
    seed_database()
    
    # Execute dynamic test
    run_dynamic_test("test.png", "ORD-1001")