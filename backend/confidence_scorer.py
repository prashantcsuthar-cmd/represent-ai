# backend/core/confidence_scorer.py

def calculate_confidence_score(
    name_similarity: float,    # 0.0 to 1.0 (Levenshtein/Jaro-Winkler)
    ela_passed: bool,          # True if Max Variance <= 30.0
    tracking_valid: bool,      # True if valid carrier format & status
    otp_verified: bool = False # True if secure OTP confirmed
) -> dict:
    """
    Computes mathematical confidence score for dispute evaluation:
    Confidence = (0.35 * NameSim) + (0.35 * ELAPass) + (0.20 * TrackingValid) + (0.10 * OTPVerified)
    """
    name_weight = 0.35 * name_similarity
    ela_weight = 0.35 if ela_passed else 0.0
    tracking_weight = 0.20 if tracking_valid else 0.0
    otp_weight = 0.10 if otp_verified else 0.0

    total_score = round((name_weight + ela_weight + tracking_weight + otp_weight) * 100, 2)

    return {
        "final_score": total_score,
        "formula_breakdown": {
            "name_similarity_weight": round(name_weight * 100, 2),
            "ela_integrity_weight": round(ela_weight * 100, 2),
            "tracking_validity_weight": round(tracking_weight * 100, 2),
            "otp_verification_weight": round(otp_weight * 100, 2)
        },
        "formula_str": "Score = (0.35 * NameSim) + (0.35 * ELA) + (0.20 * Tracking) + (0.10 * OTP)"
    }