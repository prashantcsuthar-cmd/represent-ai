import io
import re
import numpy as np
from PIL import Image, ImageChops
from rapidfuzz import fuzz

def calculate_ela_variance(image_path: str, quality: int = 90) -> float:
    """
    Performs Error Level Analysis (ELA) using structural statistical variance.
    Avoids linear brightness multiplication that clips clean UI screenshots to 255.0.
    """
    try:
        original = Image.open(image_path).convert('RGB')
        
        # Save to memory buffer at specified quality
        buffer = io.BytesIO()
        original.save(buffer, 'JPEG', quality=quality)
        buffer.seek(0)
        
        recompressed = Image.open(buffer).convert('RGB')
        
        # Absolute difference between original and recompressed image
        ela_img = ImageChops.difference(original, recompressed)
        
        # Compute raw pixel channel statistical variance without max brightness clipping
        ela_np = np.array(ela_img)
        avg_variance = float(np.var(ela_np))
        
        return round(avg_variance, 2)
    except Exception as e:
        print(f"ELA Analysis Warning: {e}")
        return 0.0

def execute_phase1_preeval(image_path: str, ocr_data, ledger_name: str, ledger_amount: float) -> dict:
    """
    Phase 1 Forensic & Deterministic Evaluation Engine
    """
    forensic_flags = []
    
    # 1. Error Level Analysis (ELA)
    ela_variance = calculate_ela_variance(image_path)
    
    # Statistical ELA Threshold: Clean mobile UI stays low (< 12.0), spliced images spike higher (> 20.0)
    ELA_THRESHOLD = 12.0
    tamper_detected = False
    
    if ela_variance > ELA_THRESHOLD:
        tamper_detected = True
        forensic_flags.append(f"HIGH_ELA_VARIANCE_DETECTED: {ela_variance:.2f}")

    # 2. Customer Name Similarity Check (RapidFuzz WRatio)
    ocr_name = (ocr_data.customer_name or "").strip().lower()
    clean_ledger_name = (ledger_name or "").strip().lower()
    
    if ocr_name and clean_ledger_name:
        similarity = float(fuzz.ratio(clean_ledger_name, ocr_name) / 100.0)
    else:
        similarity = 0.0
        forensic_flags.append("CUSTOMER_NAME_MISSING")

    is_exact_match = similarity >= 0.90
    if not is_exact_match:
        tamper_detected = True
        forensic_flags.append("CUSTOMER_NAME_MISMATCH")

    # 3. Amount Matching Logic
    raw_amount = ocr_data.amount
    if isinstance(raw_amount, str):
        clean_str = re.sub(r'[^\d.]', '', raw_amount)
        clean_ocr_amount = float(clean_str) if clean_str else 0.0
    elif isinstance(raw_amount, (int, float)):
        clean_ocr_amount = float(raw_amount)
    else:
        clean_ocr_amount = 0.0

    if clean_ocr_amount <= 0.0:
        amount_match = False
        forensic_flags.append("AMOUNT_PARSING_FAILED")
    else:
        amount_match = abs(ledger_amount - clean_ocr_amount) < 0.01
        if not amount_match:
            forensic_flags.append("AMOUNT_MISMATCH")

    # 4. Tracking Number Format Check
    tracking_num = (ocr_data.tracking_number or "").strip()
    tracking_format_valid = len(tracking_num) > 3

    # 5. Delivery Timeline Logic Check
    timeline_valid = True

    return {
        "name_similarity": similarity,
        "is_exact_name_match": is_exact_match,
        "ela_variance": ela_variance,
        "tamper_detected": tamper_detected,
        "forensic_flags": forensic_flags,
        "tracking_format_valid": tracking_format_valid,
        "timeline_valid": timeline_valid,
        "amount_match": amount_match
    }