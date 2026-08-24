from backend.state import OCRExtractedData

# Benchmark dataset containing 5 mock test cases for evaluation
EVAL_DATASET = [
    {
        "case_id": "CASE-001",
        "image_path": "test.png",
        "ledger_customer_name": "Rahul Sharma",
        "ledger_amount": 149.99,
        "expected_verdict": "REJECTED",
        "ocr_data": OCRExtractedData(
            customer_name="John Fake Person",
            order_id="ORD-99281",
            amount=149.99,
            carrier_name="UPS",
            tracking_number="1Z9999999999999999",
            delivery_status="DELIVERED",
            order_date="2026-08-01",
            delivery_date="2026-08-04"
        )
    },
    {
        "case_id": "CASE-002",
        "image_path": "test.png",
        "ledger_customer_name": "Priya Patel",
        "ledger_amount": 299.50,
        "expected_verdict": "ACCEPTED",
        "ocr_data": OCRExtractedData(
            customer_name="Priya Patel",
            order_id="ORD-44102",
            amount=299.50,
            carrier_name="FedEx",
            tracking_number="987654321012",
            delivery_status="DELIVERED",
            order_date="2026-08-02",
            delivery_date="2026-08-05"
        )
    },
    {
        "case_id": "CASE-003",
        "image_path": "test.png",
        "ledger_customer_name": "Amit Verma",
        "ledger_amount": 89.00,
        "expected_verdict": "REJECTED",
        "ocr_data": OCRExtractedData(
            customer_name="Amit Verma",
            order_id="ORD-11029",
            amount=500.00,  # Amount mismatch against ledger
            carrier_name="USPS",
            tracking_number="9400100000000000000000",
            delivery_status="DELIVERED",
            order_date="2026-08-03",
            delivery_date="2026-08-06"
        )
    },
    {
        "case_id": "CASE-004",
        "image_path": "test.png",
        "ledger_customer_name": "Sneha Reddy",
        "ledger_amount": 420.00,
        "expected_verdict": "ACCEPTED",
        "ocr_data": OCRExtractedData(
            customer_name="Sneha Reddy",
            order_id="ORD-88301",
            amount=420.00,
            carrier_name="DHL",
            tracking_number="1234567890",
            delivery_status="DELIVERED",
            order_date="2026-08-05",
            delivery_date="2026-08-08"
        )
    },
    {
        "case_id": "CASE-005",
        "image_path": "test.png",
        "ledger_customer_name": "Vikram Singh",
        "ledger_amount": 1250.00,
        "expected_verdict": "REJECTED",
        "ocr_data": OCRExtractedData(
            customer_name="Unknown Receiver",
            order_id="ORD-00921",
            amount=100.00,  # Double discrepancy (name & amount mismatch)
            carrier_name="UPS",
            tracking_number="1Z8888888888888888",
            delivery_status="IN_TRANSIT",
            order_date="2026-08-10",
            delivery_date="N/A"
        )
    }
]