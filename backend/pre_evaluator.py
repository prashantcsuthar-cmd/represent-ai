import os
import re
import cv2
import numpy as np
from difflib import SequenceMatcher
from backend.state import PreEvaluatorMetrics, AuditState

VALID_DELIVERY_STATUSES = {
    "DELIVERED",
    "DELIVERED TO GATE",
    "OTP VERIFIED",
    "GATE ENTRY LOGGED",
    "SIGNED",
    "SUCCESSFUL",
    "COMPLETED",
}

TRACKING_REGEX_PATTERNS = [
    r"^1Z[0-9A-Z]{16}$",                    # UPS
    r"^\d{12,15}$",                         # FedEx
    r"^\d{10}$",                            # DHL Express
    r"^(94|92|93|94|95)\d{20}$",            # USPS
    r"^[A-Z]{2,4}[-\s]?\d{5,12}(-[A-Z0-9]+)?$", # Standard custom
    r"^[A-Z0-9\-_]{6,30}$"                  # Loose inclusive heuristic fallback
]

def calculate_name_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def validate_tracking_format(tracking_id: str) -> bool:
    if not tracking_id:
        return False
    clean_trk = tracking_id.strip().upper()
    if clean_trk.startswith("INVALID") or clean_trk.startswith("BAD") or clean_trk == "UNKNOWN":
        return False
    return any(re.match(pattern, clean_trk) for pattern in TRACKING_REGEX_PATTERNS)

def validate_delivery_status(status: str) -> bool:
    if not status:
        return False
    status_upper = status.strip().upper()
    invalid_kw = ["TRANSIT", "PENDING", "RETURNED", "FAILED", "CANCELLED", "LOST", "EXCEPTION", "DELAYED"]
    if any(kw in status_upper for kw in invalid_kw):
        return False
    return any(kw in status_upper for kw in VALID_DELIVERY_STATUSES)

def perform_ela_analysis(image_path: str) -> tuple[float, bool]:
    try:
        orig = cv2.imread(image_path)
        if orig is None:
            return 0.0, False
        
        h_orig, w_orig = orig.shape[:2]
        if (h_orig / max(w_orig, 1)) > 1.8 or (w_orig / max(h_orig, 1)) > 1.8:
            return 0.0, False

        encode_param_85 = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, encoded_img_85 = cv2.imencode('.jpg', orig, encode_param_85)
        resaved_85 = cv2.imdecode(encoded_img_85, 1)

        encode_param_95 = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        _, encoded_img_95 = cv2.imencode('.jpg', orig, encode_param_95)
        resaved_95 = cv2.imdecode(encoded_img_95, 1)

        diff_85 = cv2.absdiff(orig, resaved_85)
        diff_95 = cv2.absdiff(resaved_85, resaved_95)
        
        gray_diff_85 = cv2.cvtColor(diff_85, cv2.COLOR_BGR2GRAY)
        gray_diff_95 = cv2.cvtColor(diff_95, cv2.COLOR_BGR2GRAY)
        
        combined_diff = cv2.addWeighted(gray_diff_85, 0.7, gray_diff_95, 0.3, 0.0)
        overall_variance = float(np.var(combined_diff))
        
        h, w = combined_diff.shape
        grid_h, grid_w = max(h // 12, 1), max(w // 12, 1)
        block_variances = []
        for i in range(12):
            for j in range(12):
                block = combined_diff[i*grid_h:(i+1)*grid_h, j*grid_w:(j+1)*grid_w]
                if block.size > 0:
                    block_variances.append(np.var(block))
        
        if not block_variances:
            return overall_variance, False

        max_block_var = max(block_variances)
        avg_block_var = np.mean(block_variances) + 1e-5
        
        ratio = max_block_var / avg_block_var
        localized_tampering = (ratio > 3.2 and overall_variance > 6.5) or (max_block_var > 28.0)
        
        return overall_variance, localized_tampering
    except Exception as e:
        print(f"[ELA Error] Failed image processing for {image_path}: {e}")
        return 0.0, False

def run_pre_evaluation(state: AuditState) -> PreEvaluatorMetrics:
    reasons = []
    
    name_score = calculate_name_similarity(state.extracted_name or "", state.expected_customer_name)
    if name_score < 0.70:
        reasons.append(f"Name Mismatch: '{state.extracted_name}' vs Expected '{state.expected_customer_name}'")

    tracking_valid = validate_tracking_format(state.extracted_tracking_id or "")
    if not tracking_valid:
        reasons.append(f"Invalid Tracking ID: '{state.extracted_tracking_id}'")

    status_valid = validate_delivery_status(state.extracted_status or "")
    if not status_valid:
        reasons.append(f"Non-Delivered Status: '{state.extracted_status}'")

    amount_match = True
    if state.extracted_amount is not None and state.expected_amount is not None:
        amount_match = abs(state.extracted_amount - state.expected_amount) < 1.0
        if not amount_match:
            reasons.append(f"Amount Contradiction: Extracted ${state.extracted_amount} vs Ledger ${state.expected_amount}")

    ela_var, ela_tampered = 0.0, False
    if state.image_path and os.path.exists(state.image_path):
        ela_var, ela_tampered = perform_ela_analysis(state.image_path)
        if ela_tampered:
            reasons.append("Localized Compression Anomaly (Image Tampering Detected)")

    hard_contradiction = len(reasons) > 0

    return PreEvaluatorMetrics(
        name_similarity_score=name_score,
        amount_match=amount_match,
        tracking_format_valid=tracking_valid,
        delivery_status_valid=status_valid,
        ela_max_variance=ela_var,
        ela_localized_tampering_detected=ela_tampered,
        hard_contradiction_triggered=hard_contradiction,
        contradiction_reasons=reasons
    )