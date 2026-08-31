import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auditor_agent import audit_dispute
from evals.benchmark_metrics import BenchmarkReport

def generate_benchmark_suite():
    cases = []
    
    # 1. Image Cases (1-30)
    for i in range(1, 31):
        is_tampered = (i > 25)
        is_valid_trk = (i <= 20)
        cases.append({
            "case_id": f"SYN-IMG-{i:02d}",
            "category": "Image POD Evaluation",
            "raw_text": f"Customer Name: Prashanth C\nTracking ID: {'1Z12345678901234' + str(i) if is_valid_trk else 'BAD-TRK'}\nStatus: DELIVERED\nAmount: $150.00",
            "ledger_customer_name": "Prashanth C",
            "ledger_amount": 150.00,
            "ela_max_variance": 80.0 if is_tampered else 12.0,
            "expected_verdict": "ACCEPTED" if (is_valid_trk and not is_tampered) else "REJECTED"
        })

    # 2. Text Cases (31-100)
    for i in range(31, 101):
        if i <= 60:
            # Clean
            raw_text = f"Customer Name: Prashanth C\nTracking ID: 1Z99999999999999{i}\nStatus: DELIVERED\nAmount: $150.00"
            expected = "ACCEPTED"
            cat = "Clean Text POD"
            name = "Prashanth C"
        elif i <= 80:
            # Fuzzy
            raw_text = f"Customer Name: Prashant C\nTracking ID: 1Z88888888888888{i}\nStatus: DELIVERED\nAmount: $150.00"
            expected = "ACCEPTED"
            cat = "Fuzzy Recipient Name"
            name = "Prashanth C"
        else:
            # Non-delivered/Bad Tracking
            raw_text = f"Customer Name: Prashanth C\nTracking ID: INVALID-{i}\nStatus: IN_TRANSIT\nAmount: $150.00"
            expected = "REJECTED"
            cat = "Malformed / In-Transit"
            name = "Prashanth C"

        cases.append({
            "case_id": f"SYN-TXT-{i:03d}",
            "category": cat,
            "raw_text": raw_text,
            "ledger_customer_name": name,
            "ledger_amount": 150.00,
            "ela_max_variance": 5.0,
            "expected_verdict": expected
        })

    return cases

def run_benchmark():
    cases = generate_benchmark_suite()
    report = BenchmarkReport()

    print("\n--- STARTING BENCHMARK EVALUATION RUNNER ---")
    start_time = time.time()

    for case in cases:
        res = audit_dispute(case, offline_mode=True)
        actual = res["verdict"]
        expected = case["expected_verdict"]

        if actual == "ACCEPTED" and expected == "ACCEPTED":
            report.tp += 1
        elif actual == "REJECTED" and expected == "REJECTED":
            report.tn += 1
        elif actual == "ACCEPTED" and expected == "REJECTED":
            report.fp += 1
        elif actual == "REJECTED" and expected == "ACCEPTED":
            report.fn += 1

    report.compute()
    elapsed = time.time() - start_time

    print("\n" + "="*50)
    print("         BENCHMARK FORENSIC REPORT          ")
    print("="*50)
    print(f"Total Test Cases Evaluated: {report.total_cases}")
    print(f"True Positives (TP)       : {report.tp}")
    print(f"True Negatives (TN)       : {report.tn}")
    print(f"False Positives (FP/FAR)  : {report.fp}")
    print(f"False Negatives (FN/FRR)  : {report.fn}")
    print("-" * 50)
    print(f"Accuracy                  : {report.accuracy:.2f}%")
    print(f"Precision                 : {report.precision:.2f}%")
    print(f"Recall (Sensitivity)      : {report.recall:.2f}%")
    print(f"F1-Score                  : {report.f1_score:.2f}%")
    print(f"False Acceptance Rate     : {report.far:.2f}% (Lower is better)")
    print(f"False Rejection Rate      : {report.frr:.2f}%")
    print(f"Execution Time            : {elapsed:.2f}s")
    print("="*50)

if __name__ == "__main__":
    run_benchmark()