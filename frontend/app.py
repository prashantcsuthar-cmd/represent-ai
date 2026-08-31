import os
import sys
import tempfile
import pandas as pd
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator import DisputeOrchestrator
from backend.state import GateDecision
from backend.evals.run_evals import run_pipeline_evaluation

st.set_page_config(
    page_title="Represent AI | Autonomous Dispute Defense",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #0F172A; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1rem; color: #475569; margin-bottom: 1.5rem; }
    .badge-clean { background-color: #DCFCE7; color: #166534; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid #BBF7D0; }
    .badge-ambiguous { background-color: #FEF08A; color: #854D0E; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid #FEF08A; }
    .badge-hardfail { background-color: #FEE2E2; color: #991B1B; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid #FECACA; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛡️ Represent AI: Hybrid Deterministic-Gated Dispute Defense</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Fintech Chargeback Defense Engine: Forensics, Gated Rules, & HITL Review Escalation</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Single Document Audit", "📊 System Benchmark & Evals Dashboard"])

with tab1:
    st.sidebar.header("📊 Ground Truth Ledger Input")
    ledger_name = st.sidebar.text_input("Expected Customer Name", value="Vikram Singh")
    ledger_amount = st.sidebar.number_input("Expected Amount ($)", value=150.00, step=10.0)
    ledger_tracking = st.sidebar.text_input("Expected Tracking ID", value="TRK-7788")

    uploaded_file = st.file_uploader("Upload Disputed Evidence Document (PNG, JPG, JPEG, TXT)", type=["png", "jpg", "jpeg", "txt"])

    if uploaded_file is not None:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_file_path = tmp_file.name

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📄 Uploaded Evidence Document")
            if file_ext in [".png", ".jpg", ".jpeg"]:
                image = Image.open(temp_file_path)
                st.image(image, use_container_width=True)
            else:
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    st.code(f.read(), language="text")

        with col2:
            st.subheader("⚡ Automated Pipeline Execution")
            if st.button("🚀 Run Hybrid Forensic Audit", type="primary", use_container_width=True):
                with st.spinner("Executing Deterministic Gates & LLM Synthesis..."):
                    try:
                        orchestrator = DisputeOrchestrator()
                        final_state = orchestrator.process_dispute(
                            file_path=temp_file_path,
                            ledger_customer_name=ledger_name,
                            ledger_amount=ledger_amount,
                            ledger_tracking_id=ledger_tracking,
                            generate_pdf=True
                        )
                        st.session_state["final_state"] = final_state
                        st.success("Audit Execution Complete!")
                    except Exception as e:
                        st.error(f"Execution Error: {str(e)}")

    if "final_state" in st.session_state:
        state = st.session_state["final_state"]
        auditor = state.auditor_output or {}
        verdict = auditor.get("authenticity_verdict", "AMBIGUOUS")
        reliability_score = auditor.get("confidence_score", 0.0)

        st.markdown("---")
        st.header("🎯 Audit Verdict & Evidence Reliability")

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            if verdict == GateDecision.CLEAN.value:
                st.markdown(f"**Gate Decision**<br><span class='badge-clean'>✅ CLEAN</span>", unsafe_allow_html=True)
            elif verdict == GateDecision.AMBIGUOUS.value:
                st.markdown(f"**Gate Decision**<br><span class='badge-ambiguous'>⚠️ AMBIGUOUS</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"**Gate Decision**<br><span class='badge-hardfail'>🚨 HARD FAIL</span>", unsafe_allow_html=True)

        with m_col2:
            st.metric("Evidence Reliability Score", f"{reliability_score:.1f}%")
            
        with m_col3:
            ela_val = state.metrics.ela_max_variance if state.metrics else 0.0
            st.metric("ELA Variance", f"{ela_val:.2f}")
            
        with m_col4:
            sim_val = state.metrics.name_similarity_score if state.metrics else 0.0
            st.metric("Name Similarity", f"{sim_val:.2f}")

        if state.human_review_required or verdict == GateDecision.AMBIGUOUS.value:
            st.warning("⚠️ **Human-in-the-Loop (HITL) Review Triggered**: The system encountered ambiguous signals and routed this case for manual compliance review[cite: 5].")
            with st.expander("🛠️ Reviewer Override Dashboard", expanded=True):
                rev_col1, rev_col2 = st.columns(2)
                with rev_col1:
                    st.write("**Extracted Evidence Summary:**")
                    st.json({
                        "extracted_name": state.extracted_name,
                        "extracted_amount": state.extracted_amount,
                        "extracted_tracking": state.extracted_tracking_id,
                        "contradictions": state.metrics.contradiction_reasons if state.metrics else []
                    })
                with rev_col2:
                    st.write("**Manual Review Action:**")
                    override_decision = st.radio("Override System Verdict?", ["Maintain Escalation", "Approve & Override (Clean)", "Reject Document"])
                    if st.button("Confirm Reviewer Override"):
                        if "Approve" in override_decision:
                            state.gate_decision = GateDecision.CLEAN
                            st.success("Case manually overridden to CLEAN.")
                        elif "Reject" in override_decision:
                            state.gate_decision = GateDecision.HARD_FAIL
                            st.error("Case manually overridden to HARD FAIL.")
                        st.rerun()

        st.subheader("📋 LLM Synthesis & Explanation")
        st.info(state.llm_synthesis or "No synthesis available.")

        st.subheader("📊 Phase 1 Deterministic Metric Breakdown")
        if state.metrics:
            metrics_table = [
                {"Metric": "Customer Name Similarity", "Value": f"{state.metrics.name_similarity_score:.2f}", "Status": "Passed" if state.metrics.name_similarity_score >= 0.85 else "Flagged"},
                {"Metric": "ELA Tampering Detection", "Value": str(state.metrics.ela_localized_tampering_detected), "Status": "Clean" if not state.metrics.ela_localized_tampering_detected else "Anomaly Detected"},
                {"Metric": "Tracking Format Validity", "Value": str(state.metrics.tracking_format_valid), "Status": "Valid" if state.metrics.tracking_format_valid else "Invalid Format"},
                {"Metric": "Ledger Amount Match", "Value": str(state.metrics.amount_match), "Status": "Matched" if state.metrics.amount_match else "Mismatch"}
            ]
            st.table(metrics_table)

        if state.pdf_path and os.path.exists(state.pdf_path):
            st.markdown("---")
            st.subheader("📥 Export Official Defense Brief")
            with open(state.pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Defense Brief (PDF)",
                    data=pdf_file,
                    file_name=os.path.basename(state.pdf_path),
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )

with tab2:
    st.header("📈 Production Forensic Benchmark Suite")
    st.write("Run evaluation across the test dataset to generate live precision, recall, and accuracy metrics[cite: 8].")

    if st.button("▶️ Execute Benchmark Suite", type="primary"):
        with st.spinner("Evaluating dataset across pipeline layers..."):
            report = run_pipeline_evaluation()
            if report:
                st.success("Benchmark Run Complete!")
                
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Accuracy", f"{report.accuracy:.1f}%")
                b2.metric("Precision", f"{report.precision:.1f}%")
                b3.metric("Recall", f"{report.recall:.1f}%")
                b4.metric("F1 Score", f"{report.f1_score:.1f}%")

                st.subheader("📋 Confusion Matrix Breakdown")
                cm_data = {
                    "Actual Authentic": [f"True Positives: {report.tp}", f"False Negatives: {report.fn}"],
                    "Actual Tampered": [f"False Positives: {report.fp}", f"True Negatives: {report.tn}"]
                }
                cm_df = pd.DataFrame(cm_data, index=["Predicted Authentic", "Predicted Tampered"])
                st.table(cm_df)