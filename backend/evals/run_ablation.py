import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from backend.ocr_engine import extract_document_entities_safe
from backend.pre_evaluator import run_pre_evaluation
from backend.auditor_agent import audit_dispute
from backend.state import AuditState
from backend.evals.benchmark_metrics import BenchmarkReport
from backend.evals.run_evals import load_dataset


def evaluate_with_mode(dataset, disable_ela=False, disable_pre_eval=False):
    report = BenchmarkReport()

    for sample in dataset:
        with open(sample["image_path"], "rb") as f:
            file_bytes = f.read()

        ocr_res = extract_document_entities_safe(file_bytes)

        if disable_pre_eval:
            # Baseline: Direct pass-through without heuristic validation
            ela_var = 0.0 if disable_ela else 0.0
            audit_payload = {
                "case_id": sample["case_id"],
                "category": "Raw OCR Only",
                "raw_text": f"Customer: {ocr_res.customer_name}\nTracking: {ocr_res.tracking_number}\nStatus: {ocr_res.delivery_status}\nAmount: {ocr_res.amount}",
                "ledger_customer_name": sample["expected_customer_name"],
                "ledger_amount": sample["expected_amount"],
                "ela_max_variance": 0.0,
                "ela_tamper_detected": False
            }
        else:
            audit_state = AuditState(
                extracted_name=ocr_res.customer_name,
                extracted_amount=ocr_res.amount,
                extracted_tracking_id=ocr_res.tracking_number,
                extracted_status=ocr_res.delivery_status,
                expected_customer_name=sample["expected_customer_name"],
                expected_amount=sample["expected_amount"],
                image_path=None if disable_ela else sample["image_path"]
            )
            metrics = run_pre_evaluation(audit_state)

            audit_payload = {
                "case_id": sample["case_id"],
                "category": f"Ablation (ELA Disabled={disable_ela})",
                "raw_text": f"Customer: {ocr_res.customer_name}\nTracking: {ocr_res.tracking_number}\nStatus: {ocr_res.delivery_status}\nAmount: {ocr_res.amount}",
                "ledger_customer_name": sample["expected_customer_name"],
                "ledger_amount": sample["expected_amount"],
                "ela_max_variance": 0.0 if disable_ela else metrics.ela_max_variance,
                "ela_tamper_detected": False if disable_ela else metrics.ela_localized_tampering_detected
            }

        res = audit_dispute(audit_payload, offline_mode=False)
        actual = res.get("verdict", "REJECTED")
        expected = sample["expected_verdict"]

        if actual == "ACCEPTED" and expected == "ACCEPTED":
            report.tp += 1
        elif actual == "REJECTED" and expected == "REJECTED":
            report.tn += 1
        elif actual == "ACCEPTED" and expected == "REJECTED":
            report.fp += 1
        else:
            report.fn += 1

    report.compute()
    return report


def run_ablation_study():
    dataset_dir = BASE_DIR / "evals" / "synthetic_images" / "dev_200"
    dataset = load_dataset(dataset_dir)

    if not dataset:
        print("[!] Dataset is empty. Cannot run ablation study.")
        return

    print("\n=======================================================")
    print("           RUNNING ABLATION STUDY EXPERIMENTS          ")
    print("=======================================================")

    print("\n[1/3] Running Full Proposed Pipeline (OCR + Pre-Eval + ELA + LLM)...")
    full_report = evaluate_with_mode(dataset, disable_ela=False, disable_pre_eval=False)

    print("\n[2/3] Running Ablation Experiment 1: Disabling ELA Forensics...")
    no_ela_report = evaluate_with_mode(dataset, disable_ela=True, disable_pre_eval=False)

    print("\n[3/3] Running Ablation Experiment 2: Disabling Pre-Evaluator (Pure OCR + LLM)...")
    ocr_only_report = evaluate_with_mode(dataset, disable_ela=True, disable_pre_eval=True)

    print("\n" + "=" * 70)
    print("                    ABLATION RESULTS SUMMARY                   ")
    print("=" * 70)
    print(f"{'Pipeline Configuration':<35} | {'Accuracy':<10} | {'Precision':<10} | {'F1-Score':<10}")
    print("-" * 70)
    print(f"{'Full Engine (Proposed)':<35} | {full_report.accuracy:>8.2f}% | {full_report.precision:>8.2f}% | {full_report.f1_score:>8.2f}%")
    print(f"{'w/o ELA Image Forensics':<35} | {no_ela_report.accuracy:>8.2f}% | {no_ela_report.precision:>8.2f}% | {no_ela_report.f1_score:>8.2f}%")
    print(f"{'w/o Heuristic Pre-Evaluator':<35} | {ocr_only_report.accuracy:>8.2f}% | {ocr_only_report.precision:>8.2f}% | {ocr_only_report.f1_score:>8.2f}%")
    print("=" * 70)


if __name__ == "__main__":
    run_ablation_study()