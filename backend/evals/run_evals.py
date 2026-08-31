import os
import sys
import time
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

from google import genai
from google.genai import types

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2] if CURRENT_FILE.parents[2].name == "represent-ai" else CURRENT_FILE.parents[1]

load_dotenv(PROJECT_ROOT / ".env")
sys.path.append(str(PROJECT_ROOT))

from backend.pre_evaluator import run_pre_evaluation
from backend.auditor_agent import run_auditor_agent_offline
from backend.state import AuditState, OCRExtractedData
from backend.evals.benchmark_metrics import BenchmarkReport
from backend.evals.eval_dataset import PROGRAMMATIC_TEXT_DATASET

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
VISION_MODEL_NAME = "gemini-3.6-flash"

VISION_PROMPT = """
You are an expert Document Vision AI and Forensic OCR parser for proof-of-delivery receipts, tabular visitor logs, and mobile delivery app screenshots.
Documents may have non-standard, noisy, or unstructured layouts. Search aggressively for recipient names, currency symbols, amount values, delivery status, and tracking strings anywhere on the page.

CRITICAL INSTRUCTIONS FOR RECIPIENT NAMES & TABLES:
- If the document is a tabular log sheet, visitor register, or handwritten ledger containing multiple rows, scan every data row and extract the primary recipient or visitor name present (e.g. look for rows containing names like "Rahul Sharma", "Vikram Singh", or specific visitors). If multiple names appear, extract the most relevant target recipient name or the first valid person name entry.
- STRICTLY IGNORE column headers, table titles, or field labels such as "Visitor Name", "Flat No", "Date", "Signature", "Parcel / Courier", "VISITOR REGISTER", or "LOG SHEET" when extracting the recipient name. Never return column header strings as the extracted name.
- For physical visitor logs or register books that do not contain digital tracking barcodes, set `extracted_tracking_id` to null instead of failing or hallucinating a code.

Examine this document for digital splicing, font inconsistencies, mismatched pixel resolutions, or pasted text bounding boxes (such as overlaid verification stamps or edited text lines).

Extract the following in raw JSON format with exact keys:
{
  "extracted_tracking_id": "Tracking code or null",
  "extracted_name": "Full recipient customer name string (excluding headers/labels) or null",
  "extracted_status": "Status string (e.g. DELIVERED, SIGNED, COMPLETED, GATE ENTRY LOGGED) or null",
  "extracted_amount": Float numeric amount value or null,
  "is_visually_tampered": Boolean true if font mismatch, pixel alignment anomaly, or digital editing is visible, else false
}
If a field is unreadable or missing, set its value to null.
"""

RAW_TEXT_FALLBACK_PROMPT = """
Extract all visible text strings from this unstructured document or mobile screenshot as a raw text block. Look very carefully for tracking numbers, carrier strings, real customer names, and amounts. Do not include introductory text.
"""

def extract_pod_details_with_retry(image_path: str, max_retries: int = 5) -> dict:
    """Extracts POD text using Gemini Vision with multi-modal forensic inspection & unstructured fallback."""
    if not os.path.exists(image_path):
        return {"extracted_name": None, "extracted_amount": None, "extracted_tracking_id": None, "extracted_status": None, "is_visually_tampered": False}

    parsed_data = {}
    for attempt in range(max_retries):
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                if h > w * 1.5:
                    img.thumbnail((768, 1024))
                else:
                    img.thumbnail((768, 768))
                
                response = client.chats.create(model=VISION_MODEL_NAME).send_message(
                    message=[img, VISION_PROMPT],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                
                parsed_data = json.loads(cleaned_text.strip())
                break
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait_time = max((2 ** attempt) * 6, 40)
                print(f"[Warning] Rate limit hit. Backing off for {wait_time}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"[Vision OCR Error] {image_path}: {e}")
                time.sleep(3)

    extracted_name = parsed_data.get("extracted_name")
    
    if extracted_name:
        upper_name = extracted_name.strip().upper()
        blacklisted_headers = ["VISITOR REGISTER", "LOG SHEET", "DELIVERY NOTE", "RECEIPT", "INVOICE", "PURCHASE ORDER"]
        if any(h in upper_name for h in blacklisted_headers):
            extracted_name = None

    extracted_tracking = parsed_data.get("extracted_tracking_id")
    extracted_status = parsed_data.get("extracted_status")
    extracted_amount = parsed_data.get("extracted_amount")
    is_tampered = bool(parsed_data.get("is_visually_tampered", False))

    if not extracted_name and not extracted_tracking:
        for attempt in range(3):
            try:
                with Image.open(image_path) as img:
                    img.thumbnail((768, 768))
                    fallback_response = client.chats.create(model=VISION_MODEL_NAME).send_message(
                        message=[img, RAW_TEXT_FALLBACK_PROMPT]
                    )
                    raw_text = fallback_response.text or ""
                    
                    filtered_lines = []
                    for line in raw_text.split('\n'):
                        cleaned_line = line.strip()
                        lower_line = cleaned_line.lower()
                        if any(lower_line.startswith(prefix) for prefix in ["here is", "sure", "the text", "certainly", "based on"]):
                            continue
                        if any(bh.lower() in cleaned_line.lower() for bh in ["visitor register", "log sheet"]):
                            continue
                        if len(cleaned_line) > 2:
                            filtered_lines.append(cleaned_line)
                    
                    sanitized_text = "\n".join(filtered_lines)
                    
                    trk_match = re.search(r'\b([A-Z0-9\-_]{6,30})\b', sanitized_text)
                    if trk_match and not extracted_tracking:
                        extracted_tracking = trk_match.group(1)
                    
                    amt_match = re.search(r'[\$£€₹]?\s*(\d{1,5}\.\d{2})', sanitized_text)
                    if amt_match and not extracted_amount:
                        try:
                            extracted_amount = float(amt_match.group(1))
                        except ValueError:
                            pass
                    
                    if any(status_kw in sanitized_text.upper() for status_kw in ["DELIVERED", "SIGNED", "SUCCESSFUL", "VERIFIED", "COMPLETED", "LOGGED"]):
                        extracted_status = extracted_status or "DELIVERED"
                        
                    if not extracted_name and filtered_lines:
                        extracted_name = filtered_lines[0]
                    break
            except Exception as fallback_err:
                if "429" in str(fallback_err) or "RESOURCE_EXHAUSTED" in str(fallback_err):
                    time.sleep(40)
                else:
                    print(f"[Fallback OCR Error] {image_path}: {fallback_err}")
                    break

    return {
        "extracted_name": extracted_name,
        "extracted_amount": float(extracted_amount) if extracted_amount is not None else None,
        "extracted_tracking_id": extracted_tracking,
        "extracted_status": extracted_status,
        "is_visually_tampered": is_tampered
    }

def run_pipeline_evaluation() -> BenchmarkReport:
    """Runs the core evaluation suite and returns the aggregated BenchmarkReport for the frontend UI."""
    report = BenchmarkReport()
    for idx, case in enumerate(PROGRAMMATIC_TEXT_DATASET, 1):
        state = AuditState(
            case_id=case["case_id"],
            extracted_name=case.get("extracted_name"),
            extracted_amount=case.get("extracted_amount"),
            extracted_tracking_id=case.get("extracted_tracking_id"),
            extracted_status=case.get("extracted_status"),
            expected_customer_name=case.get("expected_name", "Prashanth C"),
            expected_amount=case.get("expected_amount", 150.00),
            expected_tracking_id="TRK-VALID",
            image_path=None
        )
        
        metrics = run_pre_evaluation(state)
        analysis = run_auditor_agent_offline(
            ledger_customer_name=state.expected_customer_name,
            ledger_amount=state.expected_amount,
            ocr_data=OCRExtractedData(
                extracted_name=state.extracted_name,
                extracted_amount=state.extracted_amount,
                extracted_tracking_id=state.extracted_tracking_id,
                extracted_status=state.extracted_status
            ),
            metrics=metrics
        )
        
        got = analysis.authenticity_verdict
        exp = case["expected_verdict"]
        
        if got == "ACCEPTED" and exp == "ACCEPTED": report.tp += 1
        elif got == "REJECTED" and exp == "REJECTED": report.tn += 1
        elif got == "ACCEPTED" and exp == "REJECTED": report.fp += 1
        else: report.fn += 1

    report.compute()
    return report

def run_programmatic_text_benchmark():
    print("\n" + "=" * 65)
    print(" TRACK 1: PROGRAMMATIC TEXT EVALUATION (34 CASES - ZERO API COST) ")
    print("=" * 65)
    
    report = run_pipeline_evaluation()
    for idx, case in enumerate(PROGRAMMATIC_TEXT_DATASET, 1):
        print(f"[{idx:02d}/34] {case['case_id']} | Expected: {case['expected_verdict']:<8}")

    print("-" * 65)
    print(f" Track 1 Accuracy: {report.accuracy:.2f}% | Total Text Cases: 34")
    print("-" * 65)

def get_image_datasets() -> list[dict]:
    image_entries = []
    metadata_candidates = [
        PROJECT_ROOT / "evals" / "synthetic_images" / "dev_200" / "metadata.json",
        PROJECT_ROOT / "backend" / "evals" / "metadata.json",
        PROJECT_ROOT / "metadata.json",
        PROJECT_ROOT / "tests" / "fixtures" / "adversarial_dataset" / "metadata.json"
    ]
    metadata_path = next((p for p in metadata_candidates if p.exists()), None)
    
    if not metadata_path:
        return image_entries

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_list = json.load(f)
        
    authentic_name_map = {}
    for item in metadata_list:
        if "is_tampered" in item and not item.get("is_tampered", False):
            wb = item.get("waybill_no")
            name = item.get("recipient_name")
            if wb and name:
                authentic_name_map[wb] = name

    for item in metadata_list:
        filename = item.get("filename")
        if not filename:
            continue
            
        possible_paths = [
            PROJECT_ROOT / "evals" / "synthetic_images" / "dev_200" / ("tampered" if item.get("is_tampered") else "authentic") / filename,
            PROJECT_ROOT / "tests" / "fixtures" / "adversarial_dataset" / "held_out_100" / filename,
            PROJECT_ROOT / "tests" / "fixtures" / "adversarial_dataset" / filename,
            PROJECT_ROOT / "evals" / "synthetic_images" / "dev_200" / filename
        ]
        img_path = next((p for p in possible_paths if p.exists()), None)
        if not img_path:
            continue

        if "is_tampered" in item:
            is_tampered = item.get("is_tampered", False)
            expected_verdict = "REJECTED" if is_tampered else "ACCEPTED"
            waybill = item.get("waybill_no") or "TRK-UNKNOWN"
            
            if is_tampered:
                expected_name = authentic_name_map.get(waybill, item.get("recipient_name") or "Unknown Customer")
            else:
                expected_name = item.get("recipient_name") or "Unknown Customer"
                
            expected_tracking = waybill
        else:
            gt = item.get("ground_truth", {})
            is_authentic = gt.get("is_authentic", True)
            expected_verdict = "ACCEPTED" if is_authentic else "REJECTED"
            expected_name = gt.get("customer_name") or "Unknown Customer"
            expected_tracking = gt.get("tracking_number") or "TRK-UNKNOWN"

        image_entries.append({
            "path": img_path,
            "expected_verdict": expected_verdict,
            "expected_name": expected_name,
            "expected_tracking": expected_tracking
        })

    return image_entries

def run_multimodal_image_benchmark(rate_limit_delay: float = 25.0):
    print("\n" + "=" * 65)
    print(" TRACK 2: MULTIMODAL VISION BENCHMARK (PHYSICAL POD IMAGES) ")
    print(f" Throttling: {rate_limit_delay}s per image (Safe Free Tier Quota)")
    print("=" * 65)

    image_entries = get_image_datasets()

    if not image_entries:
        print(f"❌ No dataset image files found under {PROJECT_ROOT}")
        return

    report = BenchmarkReport()
    latencies = []

    print(f"Found {len(image_entries)} image test cases across dataset directories.\n")

    for idx, item in enumerate(image_entries, 1):
        img_path = item["path"]
        expected_verdict = item["expected_verdict"]
        expected_name = item["expected_name"]
        expected_tracking = item["expected_tracking"]

        doc_start = time.time()
        print(f"[{idx:02d}/{len(image_entries)}] Processing: {img_path.name}")

        extracted_dict = extract_pod_details_with_retry(str(img_path))
        
        ocr_data = OCRExtractedData(
            extracted_name=extracted_dict.get("extracted_name"),
            extracted_amount=extracted_dict.get("extracted_amount"),
            extracted_tracking_id=extracted_dict.get("extracted_tracking_id"),
            extracted_status=extracted_dict.get("extracted_status")
        )

        state = AuditState(
            case_id=f"IMG-{img_path.stem}",
            extracted_name=ocr_data.extracted_name,
            extracted_amount=ocr_data.extracted_amount,
            extracted_tracking_id=ocr_data.extracted_tracking_id,
            extracted_status=ocr_data.extracted_status,
            expected_customer_name=expected_name,
            expected_amount=150.00,
            expected_tracking_id=expected_tracking,
            image_path=str(img_path)
        )

        metrics = run_pre_evaluation(state)
        
        if extracted_dict.get("is_visually_tampered") or metrics.ela_localized_tampering_detected:
            metrics.ela_localized_tampering_detected = True
            metrics.hard_contradiction_triggered = True
            if "Visual Tampering / Font Anomaly Detected (Multi-Modal Gate)" not in metrics.contradiction_reasons:
                metrics.contradiction_reasons.append("Visual Tampering / Font Anomaly Detected (Multi-Modal Gate)")

        analysis = run_auditor_agent_offline(
            ledger_customer_name=expected_name,
            ledger_amount=150.00,
            ocr_data=ocr_data,
            metrics=metrics
        )
        
        doc_latency = time.time() - doc_start
        latencies.append(doc_latency)

        got = analysis.authenticity_verdict

        if got == "ACCEPTED" and expected_verdict == "ACCEPTED": report.tp += 1
        elif got == "REJECTED" and expected_verdict == "REJECTED": report.tn += 1
        elif got == "ACCEPTED" and expected_verdict == "REJECTED": report.fp += 1
        else: report.fn += 1

        print(f"   └─ Verdict: {got:<8} (Expected: {expected_verdict:<8}) | Latency: {doc_latency:.2f}s | Score: {analysis.confidence_score}")
        if metrics.contradiction_reasons:
            print(f"   └─ Flags: {'; '.join(metrics.contradiction_reasons)}")

        if idx < len(image_entries):
            print(f"   ⏳ Throttling for {rate_limit_delay}s to respect free tier limits...")
            time.sleep(rate_limit_delay)

    report.compute()
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 65)
    print(" TRACK 2 EVALUATION SUMMARY ")
    print("=" * 65)
    print(f" Total Images Tested : {len(image_entries)}")
    print(f" Overall Accuracy    : {report.accuracy:.2f}%")
    print(f" Precision           : {report.precision:.2f}%")
    print(f" Recall              : {report.recall:.2f}%")
    print(f" F1 Score            : {report.f1_score:.2f}%")
    print(f" Mean Latency        : {avg_latency:.2f}s / doc")
    print("=" * 65)

if __name__ == "__main__":
    run_programmatic_text_benchmark()
    run_multimodal_image_benchmark()