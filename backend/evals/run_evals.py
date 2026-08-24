import pandas as pd
from typing import Tuple, Dict, Any, List
from backend.evals.eval_dataset import EVAL_DATASET
from backend.orchestrator import DisputeOrchestrator


def run_evaluation_suite(api_key: str) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Executes the benchmark evaluation harness across all mock test cases.
    Returns:
        - pd.DataFrame: Results matrix formatted for Streamlit UI
        - Dict[str, float]: Calculated classification metrics (Accuracy, Precision, Recall, F1)
    """
    orchestrator = DisputeOrchestrator(gemini_api_key=api_key)
    results: List[Dict[str, Any]] = []

    # Counters for confusion matrix (Positive Class = REJECTED / Fraudulent Dispute)
    tp = 0  # True Positive: Predicted REJECTED, Expected REJECTED
    fp = 0  # False Positive: Predicted REJECTED, Expected ACCEPTED
    tn = 0  # True Negative: Predicted ACCEPTED, Expected ACCEPTED
    fn = 0  # False Negative: Predicted ACCEPTED, Expected REJECTED

    for test_case in EVAL_DATASET:
        # Run pipeline
        state = orchestrator.process_dispute(
            image_path=test_case["image_path"],
            ocr_data=test_case["ocr_data"],
            ledger_customer_name=test_case["ledger_customer_name"],
            ledger_amount=test_case["ledger_amount"],
            generate_pdf=False  # Skip PDF generation for faster evaluation runs
        )

        auditor_output = state.auditor_output or {}
        predicted_verdict = auditor_output.get("authenticity_verdict", "UNKNOWN")
        confidence_score = auditor_output.get("confidence_score", 0.0)
        expected_verdict = test_case["expected_verdict"]

        is_correct = predicted_verdict == expected_verdict

        # Metric calculation logic
        if predicted_verdict == "REJECTED" and expected_verdict == "REJECTED":
            tp += 1
        elif predicted_verdict == "REJECTED" and expected_verdict == "ACCEPTED":
            fp += 1
        elif predicted_verdict == "ACCEPTED" and expected_verdict == "ACCEPTED":
            tn += 1
        elif predicted_verdict == "ACCEPTED" and expected_verdict == "REJECTED":
            fn += 1

        results.append({
            "Customer Name": test_case["ledger_customer_name"],
            "Order ID": test_case["ocr_data"].order_id,
            "Expected Verdict": expected_verdict,
            "Predicted Verdict": predicted_verdict,
            "Status": "✅ Pass" if is_correct else "❌ Fail",
            "Confidence": f"{confidence_score * 100:.1f}%",
            "Forensic Tamper Detected": state.metrics.ela_tamper_detected if state.metrics else False
        })

    # Convert results into a Pandas DataFrame for Streamlit rendering
    df_results = pd.DataFrame(results)

    # Calculate standard classification metrics
    total = len(EVAL_DATASET)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score
    }

    return df_results, metrics


if __name__ == "__main__":
    import os
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        df, m = run_evaluation_suite(api_key=key)
        print("\nEvaluation Results Matrix:")
        print(df)
        print("\nMetrics Summary:", m)
    else:
        print("Please set GEMINI_API_KEY environment variable to test locally.")