import os
import datetime
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.state import SystemState


def generate_defense_brief_pdf(state: SystemState, output_dir: str = "output") -> str:
    """
    Generates a professional Merchant Defense Brief PDF based on Orchestrator SystemState.
    Returns the absolute path to the generated PDF.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    order_id = state.ocr_data.order_id if (state.ocr_data and state.ocr_data.order_id and state.ocr_data.order_id != "Null") else "UNKNOWN_ORDER"
    filename = f"Official_Defense_Brief_{order_id}.pdf"
    output_filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        output_filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # 1. Header Section
    story.append(Paragraph("OFFICIAL MERCHANT DEFENSE BRIEF", title_style))
    story.append(Paragraph(f"RepresentAI Automated Dispute Audit System | Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    # Get Auditor Output
    auditor = state.auditor_output or {}
    verdict = auditor.get("authenticity_verdict", "UNKNOWN")
    confidence = auditor.get("confidence_score", 0.0)
    key_findings = auditor.get("key_findings", [])
    mismatch_breakdown = auditor.get("mismatch_breakdown", "No breakdown available.")

    verdict_color = colors.HexColor('#DC2626') if verdict in ['REJECTED', 'SUSPICIOUS'] else colors.HexColor('#16A34A')

    # 2. Case Summary Table
    meta_data = [
        [Paragraph("<b>Order ID:</b>", body_style), Paragraph(str(order_id), body_style),
         Paragraph("<b>Audit Verdict:</b>", body_style), Paragraph(f"<font color='{verdict_color.hexval()}'><b>{verdict}</b></font>", body_style)],
        [Paragraph("<b>Customer (Ledger):</b>", body_style), Paragraph(state.ledger_customer_name, body_style),
         Paragraph("<b>Confidence Score:</b>", body_style), Paragraph(f"{confidence * 100:.1f}%", body_style)],
        [Paragraph("<b>Customer (Receipt):</b>", body_style), Paragraph(state.ocr_data.customer_name or "N/A", body_style),
         Paragraph("<b>Transaction Amount:</b>", body_style), Paragraph(f"${state.ledger_amount:.2f}", body_style)],
        [Paragraph("<b>Carrier Tracking:</b>", body_style), Paragraph(f"{state.ocr_data.carrier_name or 'N/A'} - {state.ocr_data.tracking_number or 'N/A'}", body_style),
         Paragraph("<b>Delivery Status:</b>", body_style), Paragraph(state.ocr_data.delivery_status or "N/A", body_style)]
    ]

    meta_table = Table(meta_data, colWidths=[120, 150, 120, 150])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # 3. Phase 1 Forensic Analysis Metrics
    story.append(Paragraph("1. Phase 1 Deterministic Forensics & ELA Metrics", heading_style))
    metrics = state.metrics

    if metrics:
        name_score = f"{metrics.name_similarity_score:.2f}"
        ela_var = f"{metrics.ela_max_variance:.1f}"
        tamper_status = "DETECTED" if metrics.ela_tamper_detected else "CLEAN"
        tamper_color = "#DC2626" if metrics.ela_tamper_detected else "#16A34A"

        forensic_data = [
            [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Observed Value</b>", body_style), Paragraph("<b>Status / Evaluation</b>", body_style)],
            [Paragraph("Name Similarity Score", body_style), Paragraph(name_score, body_style), Paragraph("Exact Match" if metrics.is_name_exact_match else "Mismatch Detected", body_style)],
            [Paragraph("ELA Max Pixel Variance", body_style), Paragraph(ela_var, body_style), Paragraph(f"<font color='{tamper_color}'><b>{tamper_status}</b></font>", body_style)],
            [Paragraph("Tracking Format Valid", body_style), Paragraph("Yes" if metrics.tracking_format_valid else "No", body_style), Paragraph("Valid Format" if metrics.tracking_format_valid else "Invalid Format", body_style)],
            [Paragraph("Delivery Timeline Valid", body_style), Paragraph("Yes" if metrics.timeline_valid else "No", body_style), Paragraph("Aligned" if metrics.timeline_valid else "Anomaly Detected", body_style)],
            [Paragraph("Ledger Amount Match", body_style), Paragraph("Yes" if metrics.amount_match else "No", body_style), Paragraph("Matched" if metrics.amount_match else "Discrepancy", body_style)]
        ]

        forensic_table = Table(forensic_data, colWidths=[180, 140, 220])
        forensic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(forensic_table)

    story.append(Spacer(1, 15))

    # 4. Phase 2 Auditor Findings & Mismatch Breakdown
    story.append(Paragraph("2. Phase 2 AI Forensic Auditor Synthesis", heading_style))
    story.append(Paragraph(f"<b>Detailed Analysis:</b> {mismatch_breakdown}", body_style))
    story.append(Spacer(1, 8))

    if key_findings:
        story.append(Paragraph("<b>Key Findings:</b>", body_style))
        for finding in key_findings:
            story.append(Paragraph(f"• {finding}", body_style))
        story.append(Spacer(1, 10))

    # 5. Formal Legal / Merchant Representation Statement
    story.append(Paragraph("3. Formal Representation", heading_style))
    if verdict in ["REJECTED", "SUSPICIOUS"]:
        defense_text = (
            f"Based on the combined forensic and LLM evaluation, this dispute claim is formally rejected. "
            f"The supporting documentation provided displays identity mismatch (Name Similarity: {metrics.name_similarity_score if metrics else 'N/A'}) "
            f"and digital image manipulation flags. The merchant requests immediate reversal/dismissal of the chargeback claim."
        )
    else:
        defense_text = (
            f"The documentation provided aligns with all customer ledger records and postal carrier tracking signals. "
            f"All forensic verification checks passed cleanly. The transaction of ${state.ledger_amount:.2f} is legitimate and fully fulfilled."
        )

    story.append(Paragraph(defense_text, body_style))
    story.append(Spacer(1, 20))

    # Footer line
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceAfter=10))
    story.append(Paragraph("Generated automatically by RepresentAI Dispute Defense Pipeline.", subtitle_style))

    # Build PDF
    doc.build(story)
    return os.path.abspath(output_filepath)