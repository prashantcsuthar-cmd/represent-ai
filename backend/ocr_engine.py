import os
import json
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

VISION_PROMPT = """
You are an expert Document Vision AI for a Payment Dispute Automation System.
Analyze the provided Proof of Delivery (POD) document or text and extract the following:

Return ONLY a valid JSON object matching this schema:
{
  "extracted_name": "Full recipient name string or null",
  "extracted_amount": Float or null,
  "extracted_tracking_id": "Tracking ID string or null",
  "extracted_status": "Status string (e.g., DELIVERED, IN_TRANSIT) or null"
}
"""

def extract_document_entities_safe(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {
            "extracted_name": None,
            "extracted_amount": None,
            "extracted_tracking_id": None,
            "extracted_status": None
        }

    try:
        # Handle text files directly without PIL
        if file_path.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[f"Extract the required JSON fields from this delivery document text:\n{text_content}\n{VISION_PROMPT}"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)

        # Handle image files
        img = Image.open(file_path)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[img, VISION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)

    except Exception as e:
        print(f"[Document Extraction Error] {file_path}: {e}")
        return {
            "extracted_name": None,
            "extracted_amount": None,
            "extracted_tracking_id": None,
            "extracted_status": None
        }