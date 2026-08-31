import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.state import AuditState


def generate_defense_brief_pdf(state: AuditState, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    
    ocr = state.ocr_data
    order_id = getattr(ocr, "order_id", None) or state.case_id
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

    story.append(Paragraph("OFFICIAL MERCHANT DEFENSE BRIEF", title_style))
    story.append(Paragraph(f"RepresentAI Automated Dispute Audit System | Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15))

    auditor = state.auditor_output or {}
    verdict = auditor.get("authenticity_verdict", "UNKNOWN")
    confidence = auditor.get("confidence_score", 0.0)
    key_findings = auditor.get("reasons", [])
    mismatch_breakdown = state.llm_synthesis or "No breakdown available."

    verdict_color = colors.HexColor('#DC2626') if verdict in ['REJECTED', 'SUSPICIOUS', 'HARD_FAIL'] else colors.HexColor('#16A34A')

    meta_data = [
        [Paragraph("<b>Case ID:</b>", body_style), Paragraph(str(state.case_id), body_style),
         Paragraph("<b>Audit Verdict:</b>", body_style), Paragraph(f"<font color='{verdict_color.hexval()}'><b>{verdict}</b></font>", body_style)],
        [Paragraph("<b>Customer (Ledger):</b>", body_style), Paragraph(state.expected_customer_name, body_style),
         Paragraph("<b>Reliability Score:</b>", body_style), Paragraph(f"{confidence:.1f}%", body_style)],
        [Paragraph("<b>Customer (Receipt):</b>", body_style), Paragraph(state.extracted_name or "N/A", body_style),
         Paragraph("<b>Transaction Amount:</b>", body_style), Paragraph(f"${state.expected_amount:.2f}", body_style)],
        [Paragraph("<b>Carrier Tracking:</b>", body_style), Paragraph(str(state.extracted_tracking_id or 'N/A'), body_style),
         Paragraph("<b>Delivery Status:</b>", body_style), Paragraph(state.extracted_status or "N/A", body_style)]
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

    story.append(Paragraph("1. Phase 1 Deterministic Forensics & ELA Metrics", heading_style))
    metrics = state.metrics

    if metrics:
        name_score = f"{metrics.name_similarity_score:.2f}"
        ela_var = f"{metrics.ela_max_variance:.1f}"
        tamper_status = "High Anomaly Risk" if metrics.ela_localized_tampering_detected else "Low Recompression Risk"
        tamper_color = "#DC2626" if metrics.ela_localized_tampering_detected else "#16A34A"

        forensic_data = [
            [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Observed Value</b>", body_style), Paragraph("<b>Status / Evaluation</b>", body_style)],
            [Paragraph("Name Similarity Score", body_style), Paragraph(name_score, body_style), Paragraph("Exact Match" if metrics.name_similarity_score >= 0.85 else "Mismatch Detected", body_style)],
            [Paragraph("ELA Max Pixel Variance", body_style), Paragraph(ela_var, body_style), Paragraph(f"<font color='{tamper_color}'><b>{tamper_status}</b></font>", body_style)],
            [Paragraph("Tracking Format Valid", body_style), Paragraph("Yes" if metrics.tracking_format_valid else "No", body_style), Paragraph("Valid Carrier Format" if metrics.tracking_format_valid else "Invalid Format", body_style)],
            [Paragraph("Delivery Status Valid", body_style), Paragraph("Yes" if metrics.delivery_status_valid else "No", body_style), Paragraph("Delivered" if metrics.delivery_status_valid else "Non-Delivered Status", body_style)],
            [Paragraph("Ledger Amount Match", body_style), Paragraph("Yes" if metrics.amount_match else "No", body_style), Paragraph("Matched" if metrics.amount_match else "Mismatch", body_style)]
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
    story.append(Paragraph("2. Phase 2 AI Forensic Auditor Synthesis", heading_style))
    story.append(Paragraph(f"<b>Detailed Analysis:</b> {mismatch_breakdown}", body_style))
    story.append(Spacer(1, 8))

    if key_findings:
        story.append(Paragraph("<b>Key Findings / Flags:</b>", body_style))
        for finding in key_findings:
            story.append(Paragraph(f"• {finding}", body_style))
        story.append(Spacer(1, 10))

    story.append(Paragraph("3. Formal Representation", heading_style))
    if verdict in ["REJECTED", "SUSPICIOUS", "HARD_FAIL"]:
        defense_text = (
            f"Based on the combined forensic and deterministic evaluation, this dispute claim is formally contested. "
            f"The supporting documentation provided displays discrepancies or verification failures. "
            f"The merchant requests upholding of the transaction charge."
        )
    else:
        defense_text = (
            f"The documentation provided aligns with all customer ledger records and postal carrier tracking signals. "
            f"All forensic verification checks passed cleanly. The transaction of ${state.expected_amount:.2f} is legitimate and fully fulfilled."
        )

    story.append(Paragraph(defense_text, body_style))
    story.append(Spacer(1, 20))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceAfter=10))
    story.append(Paragraph("Generated automatically by RepresentAI Dispute Defense Pipeline.", subtitle_style))

    doc.build(story)
    return os.path.abspath(output_filepath)