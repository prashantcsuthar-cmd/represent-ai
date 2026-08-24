import os
import json
import numpy as np
from PIL import Image
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
from rapidfuzz import fuzz
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

# Import the corrected Phase 1 functions & OCRExtractedData
from backend.pre_evaluator import calculate_ela_variance, execute_phase1_preeval
from backend.ocr_engine import extract_document_entities_safe
from backend.state import ForensicMetrics, PipelineState

load_dotenv()

class DisputeOrchestrator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                pass

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
            
        self.client = genai.Client(api_key=api_key)

    def run_phase_1(self, state: PipelineState) -> PipelineState:
        """Phase 1: Extraction & Forensic Computation."""
        ext = os.path.splitext(state.file_path)[1].lower()
        
        # Branch A: Text Logs (.txt)
        if ext == '.txt':
            with open(state.file_path, 'r', encoding='utf-8') as f:
                state.extracted_ocr_text = f.read()
            
            state.metrics.ela_max_variance = 0.0
            state.metrics.ela_avg_variance = 0.0

            prompt = f"""
            Extract structured logistics details from this document text.
            Return JSON with:
            - customer_name (string)
            - transaction_amount (float or null)
            - tracking_number (string)
            - status (string)

            Document Text:
            {state.extracted_ocr_text}
            """
            response = self.client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            state.extracted_fields = json.loads(response.text)

        # Branch B: Visual Evidence (.png, .jpg, .jpeg)
        else:
            with open(state.file_path, "rb") as f:
                file_bytes = f.read()

            # Execute OCR using the safe extractor
            ocr_data = extract_document_entities_safe(file_bytes, f"image/{ext.replace('.', '')}")
            state.extracted_fields = ocr_data.model_dump()
            state.extracted_ocr_text = ocr_data.raw_ocr_text or ""

            # Execute Phase 1 Forensic Computation (Uses non-clipping np.var)
            phase1_res = execute_phase1_preeval(
                image_path=state.file_path,
                ocr_data=ocr_data,
                ledger_name=state.ledger_customer_name,
                ledger_amount=state.ledger_amount
            )

            # Map calculated variance to PipelineState metrics
            state.metrics.ela_max_variance = phase1_res["ela_variance"]
            state.metrics.ela_avg_variance = phase1_res["ela_variance"]
            state.metrics.name_similarity_score = phase1_res["name_similarity"]
            state.metrics.amount_matched = phase1_res["amount_match"]
            state.metrics.tracking_format_valid = phase1_res["tracking_format_valid"]
            state.metrics.delivery_timeline_valid = phase1_res["timeline_valid"]

            return state

        # Name similarity fallback for text branch
        extracted_name = state.extracted_fields.get("customer_name", "")
        if extracted_name and state.ledger_customer_name:
            similarity = fuzz.ratio(str(extracted_name).lower(), str(state.ledger_customer_name).lower()) / 100.0
        else:
            similarity = 0.0
        state.metrics.name_similarity_score = round(similarity, 2)

        extracted_amount = state.extracted_fields.get("transaction_amount")
        if extracted_amount is not None and state.ledger_amount:
            state.metrics.amount_matched = abs(float(extracted_amount) - float(state.ledger_amount)) < 0.01
        else:
            state.metrics.amount_matched = True

        tracking = state.extracted_fields.get("tracking_number", "")
        state.metrics.tracking_format_valid = len(str(tracking)) > 4
        state.metrics.delivery_timeline_valid = True

        return state

    def run_phase_2(self, state: PipelineState) -> PipelineState:
        """Phase 2: LLM Forensic Auditor Agent Reasoning."""
        audit_prompt = f"""
        You are an expert Forensic Dispute Auditor. Synthesize the provided document forensic data and evaluate dispute validity.

        Ledger Ground Truth:
        - Expected Customer Name: {state.ledger_customer_name}
        - Expected Amount: ${state.ledger_amount}

        Extracted Document Data:
        - Extracted Name: {state.extracted_fields.get('customer_name')}
        - Extracted Amount: {state.extracted_fields.get('transaction_amount') or state.extracted_fields.get('amount') or 'Logistics POD (N/A)'}
        - Tracking Number: {state.extracted_fields.get('tracking_number')}
        - Delivery Status: {state.extracted_fields.get('delivery_status') or state.extracted_fields.get('status')}

        Forensic Metrics:
        - Name Similarity Score: {state.metrics.name_similarity_score} (1.0 = exact match)
        - ELA Statistical Variance: {state.metrics.ela_max_variance} (Values < 12.0 indicate genuine unedited mobile UI image; > 20.0 indicates spliced tampering)
        - Amount Matched: {state.metrics.amount_matched}

        CRITICAL EVALUATION DIRECTIVES:
        1. Contextual ELA Evaluation: Mobile app UI screenshots (BlueDart, Delhivery, etc.) naturally produce edge artifacts around text boxes. An ELA Statistical Variance under 12.0 is expected and indicates authentic compression.
        2. Proof of Delivery: Courier delivery confirmation screens verify physical fulfillment and standardly omit transaction amounts. Do not reject a document solely because an invoice amount field is absent.
        3. Verdict Criteria: If Name Similarity >= 0.85 and fulfillment is confirmed, return "VERIFIED" (or "ACCEPTED").

        Evaluate and return JSON with:
        1. "authenticity_verdict": "VERIFIED" or "REJECTED"
        2. "confidence_score": float between 0.0 and 1.0
        3. "key_findings": array of bullet point strings
        4. "mismatch_breakdown": concise explanation of evidence
        """

        response = self.client.models.generate_content(
            model='gemini-3.6-flash',
            contents=audit_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        state.auditor_output = json.loads(response.text)
        return state

    def run_phase_3(self, state: PipelineState, output_dir="output") -> PipelineState:
        """Phase 3: Legal PDF Defense Brief Generation."""
        os.makedirs(output_dir, exist_ok=True)
        tracking_num = state.extracted_fields.get('tracking_number', 'DISPUTE')
        pdf_filename = f"Official_Defense_Brief_{tracking_num}.pdf".replace("/", "_").replace("\\", "_")
        pdf_path = os.path.join(output_dir, pdf_filename)

        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#0F172A'))
        story.append(Paragraph("OFFICIAL MERCHANT DEFENSE BRIEF", title_style))
        
        sub_style = ParagraphStyle(name='SubStyle', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#64748B'))
        story.append(Paragraph(f"RepresentAI Automated Dispute Audit System | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", sub_style))
        story.append(Spacer(1, 12))

        verdict = state.auditor_output.get("authenticity_verdict", "UNKNOWN")
        verdict_color = "#16A34A" if verdict in ["ACCEPTED", "VERIFIED"] else "#DC2626"
        
        meta_data = [
            [Paragraph("<b>Order ID:</b>", styles['Normal']), Paragraph(f"{tracking_num}", styles['Normal']),
             Paragraph("<b>Audit Verdict:</b>", styles['Normal']), Paragraph(f"<font color='{verdict_color}'><b>{verdict}</b></font>", styles['Normal'])],
            [Paragraph("<b>Customer (Ledger):</b>", styles['Normal']), Paragraph(f"{state.ledger_customer_name}", styles['Normal']),
             Paragraph("<b>Confidence Score:</b>", styles['Normal']), Paragraph(f"{state.auditor_output.get('confidence_score', 0)*100:.1f}%", styles['Normal'])],
            [Paragraph("<b>Customer (Receipt):</b>", styles['Normal']), Paragraph(f"{state.extracted_fields.get('customer_name', 'N/A')}", styles['Normal']),
             Paragraph("<b>Transaction Amount:</b>", styles['Normal']), Paragraph(f"${state.ledger_amount}", styles['Normal'])],
            [Paragraph("<b>Carrier Status:</b>", styles['Normal']), Paragraph(f"{state.extracted_fields.get('delivery_status') or state.extracted_fields.get('status', 'N/A')}", styles['Normal']),
             Paragraph("<b>File Type:</b>", styles['Normal']), Paragraph(f"{os.path.splitext(state.file_path)[1].upper()}", styles['Normal'])]
        ]

        t_meta = Table(meta_data, colWidths=[120, 150, 120, 150])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 15))

        h2_style = ParagraphStyle(name='H2Style', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#1E293B'))
        story.append(Paragraph("1. Phase 1 Forensic Metrics", h2_style))
        story.append(Spacer(1, 6))

        metrics_data = [
            ["Metric", "Observed Value", "Status / Evaluation"],
            ["Name Similarity Score", str(state.metrics.name_similarity_score), "Match Confirmed" if state.metrics.name_similarity_score > 0.7 else "Mismatch Detected"],
            ["ELA Statistical Variance", str(state.metrics.ela_max_variance), "Clean / Original" if state.metrics.ela_max_variance <= 12.0 else "TAMPERING DETECTED"],
            ["Tracking Format Valid", "Yes" if state.metrics.tracking_format_valid else "No", "Valid Format" if state.metrics.tracking_format_valid else "Invalid Format"],
            ["Ledger Amount Match", "Yes" if state.metrics.amount_matched else "No", "Matched" if state.metrics.amount_matched else "Amount Mismatch"]
        ]

        t_metrics = Table(metrics_data, colWidths=[180, 160, 200])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 15))

        story.append(Paragraph("2. Phase 2 AI Forensic Auditor Synthesis", h2_style))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph(f"<b>Detailed Analysis:</b> {state.auditor_output.get('mismatch_breakdown', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph("<b>Key Findings:</b>", styles['Normal']))
        for finding in state.auditor_output.get('key_findings', []):
            story.append(Paragraph(f"• {finding}", styles['Normal']))
        
        story.append(Spacer(1, 15))

        story.append(Paragraph("3. Formal Representation Statement", h2_style))
        story.append(Spacer(1, 6))
        
        rep_text = f"Based on the forensic extraction and AI auditor synthesis, the dispute claim for tracking #{tracking_num} is formally evaluated as <b>{verdict}</b>. The merchant requests immediate reversal/dismissal of any chargeback claim based on the evidence presented."
        story.append(Paragraph(rep_text, styles['Normal']))
        
        doc.build(story)
        state.pdf_path = pdf_path
        return state

    def process_dispute(self, file_path, ledger_customer_name, ledger_amount, generate_pdf=True) -> PipelineState:
        """Runs the entire end-to-end multi-agent pipeline."""
        state = PipelineState(file_path=file_path, ledger_customer_name=ledger_customer_name, ledger_amount=ledger_amount)
        state = self.run_phase_1(state)
        state = self.run_phase_2(state)
        if generate_pdf:
            state = self.run_phase_3(state)
        return state