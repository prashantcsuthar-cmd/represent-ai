import io
import json
import re
import os
import time
from google import genai
from google.genai import types
from PIL import Image
from difflib import SequenceMatcher
from dotenv import load_dotenv

from backend.state import OCRExtractedData

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculates Levenshtein-based string similarity ratio (0.0 to 1.0)."""
    if not name1 or not name2 or name1 == "Null" or name2 == "Null":
        return 0.0
    clean1 = re.sub(r'[^a-zA-Z ]', '', name1).lower().strip()
    clean2 = re.sub(r'[^a-zA-Z ]', '', name2).lower().strip()
    return round(SequenceMatcher(None, clean1, clean2).ratio(), 2)

def extract_document_entities_safe(file_bytes: bytes, mime_type: str, max_retries: int = 3) -> OCRExtractedData:
    if not api_key:
        print("   [!] OCR Error: GEMINI_API_KEY is missing from environment!")
        return OCRExtractedData()

    client = genai.Client(api_key=api_key)

    prompt = """
    Extract the following fields from this shipping/delivery document:
    1. Recipient/Customer Name
    2. Order ID
    3. Amount
    4. Tracking Number
    5. Courier/Carrier Name
    6. Delivery Status
    7. Order Date
    8. Delivery Date

    Return strictly a JSON object with keys:
    "customer_name", "order_id", "amount", "tracking_number", "carrier_name", "delivery_status", "order_date", "delivery_date".
    Use "Null" for missing fields.
    """

    image = Image.open(io.BytesIO(file_bytes))

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            clean_text = json_match.group(0) if json_match else response.text.strip()
            data = json.loads(clean_text)
            return OCRExtractedData(**data)

        except Exception as e:
            print(f"   [!] OCR Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                print("   [!] All OCR retries exhausted. Returning default model.")
                return OCRExtractedData()