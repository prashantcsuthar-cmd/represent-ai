import os
import sys
import tempfile
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator import DisputeOrchestrator

# Page Configuration
st.set_page_config(
    page_title="Represent AI | Autonomous Dispute Defense",
    page_icon="🛡️",
    layout="wide"
)

# Premium Custom CSS Styling
st.markdown("""
    <style>
    .main-title { 
        font-size: 2.3rem; 
        font-weight: 800; 
        color: #0F172A; 
        margin-bottom: 0.2rem;
    }
    .sub-title { 
        font-size: 1.05rem; 
        color: #475569; 
        margin-bottom: 2rem; 
    }
    .badge-verified {
        background-color: #DCFCE7;
        color: #166534;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-block;
        border: 1px solid #BBF7D0;
    }
    .badge-rejected {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-block;
        border: 1px solid #FECACA;
    }
    .metric-card {
        background-color: #F8FAFC;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="main-title">🛡️ Represent AI: Autonomous Dispute Defense Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Agent Chargeback Defense: Dynamic ELA Forensics, Deterministic Matching & Automated Brief Generation</div>', unsafe_allow_html=True)

# Sidebar - Ground Truth Ledger Inputs
st.sidebar.header("📊 Ground Truth Ledger Input")
st.sidebar.caption("Enter ground-truth payment database records to cross-verify against uploaded evidence.")

ledger_name = st.sidebar.text_input("Expected Customer Name", value="Vikram Singh")
ledger_amount = st.sidebar.number_input("Expected Amount ($)", value=12500.00, step=100.0)

# Main Section File Uploader
uploaded_file = st.file_uploader("Upload Disputed Evidence Document (PNG, JPG, JPEG, TXT)", type=["png", "jpg", "jpeg", "txt"])

if uploaded_file is not None:
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    # Save uploaded file to temp path with preserved extension
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
        st.caption("Phase 1: Statistical ELA & Matching | Phase 2: AI Auditor | Phase 3: Legal Brief Generation")
        
        if st.button("🚀 Run Multi-Agent Forensic Audit", type="primary", use_container_width=True):
            with st.spinner("Executing End-to-End Forensic Dispute Pipeline..."):
                try:
                    orchestrator = DisputeOrchestrator()
                    final_state = orchestrator.process_dispute(
                        file_path=temp_file_path,
                        ledger_customer_name=ledger_name,
                        ledger_amount=ledger_amount,
                        generate_pdf=True
                    )
                    
                    st.session_state["final_state"] = final_state
                    st.success("Audit Execution Complete!")

                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")

# Display Detailed Audit Dashboard
if "final_state" in st.session_state:
    state = st.session_state["final_state"]
    auditor = state.auditor_output or {}
    verdict = auditor.get("authenticity_verdict", "UNKNOWN")
    confidence = auditor.get("confidence_score", 0.0)

    st.markdown("---")
    st.header("🎯 Audit Verdict & Forensic Synthesis")

    # Primary High-Level Summary Metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    with m_col1:
        if verdict in ["ACCEPTED", "VERIFIED"]:
            st.markdown(f"**Final Verdict**<br><span class='badge-verified'>✅ {verdict}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Final Verdict**<br><span class='badge-rejected'>🚨 {verdict}</span>", unsafe_allow_html=True)

    with m_col2:
        st.metric("Auditor Confidence", f"{confidence * 100:.1f}%")
        
    with m_col3:
        # Green status if variance is <= 12.0
        ela_val = state.metrics.ela_max_variance
        ela_delta = "Clean Image" if ela_val <= 12.0 else "High Variance"
        st.metric("ELA Statistical Variance", f"{ela_val:.2f}", delta=ela_delta, delta_color="normal" if ela_val <= 12.0 else "inverse")
        
    with m_col4:
        sim_val = state.metrics.name_similarity_score
        st.metric("Name Similarity", f"{sim_val:.2f}", delta="Exact Match" if sim_val >= 0.9 else "Mismatch")

    st.markdown("<br>", unsafe_allow_html=True)

    # Key Findings & Mismatch Breakdown
    t_col1, t_col2 = st.columns([1, 1])

    with t_col1:
        st.subheader("🔍 Key Findings & Observations")
        for finding in auditor.get("key_findings", []):
            # Dynamic status box rendering based on verdict
            if verdict in ["ACCEPTED", "VERIFIED"]:
                st.success(f"• {finding}")
            else:
                st.error(f"• {finding}")

    with t_col2:
        st.subheader("📄 Mismatch Analysis & Forensic Synthesis")
        st.info(auditor.get("mismatch_breakdown", "No breakdown available."))

    # Interactive Forensic Breakdown Table
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📊 Phase 1 Deterministic Metric Breakdown")
    
    metrics_table = [
        {"Metric": "Customer Name Similarity", "Value": f"{state.metrics.name_similarity_score:.2f}", "Evaluation": "Match Confirmed" if state.metrics.name_similarity_score >= 0.85 else "Mismatch"},
        {"Metric": "ELA Statistical Variance", "Value": f"{state.metrics.ela_max_variance:.2f}", "Evaluation": "Authentic / Original" if state.metrics.ela_max_variance <= 12.0 else "Tampering Detected"},
        {"Metric": "Tracking Format Validity", "Value": "Valid" if state.metrics.tracking_format_valid else "Invalid", "Evaluation": "Standard Courier Format"},
        {"Metric": "Ledger Amount Match", "Value": "Matched" if state.metrics.amount_matched else "Omitted (Courier POD)", "Evaluation": "Standard Logistics Behavior"}
    ]
    st.table(metrics_table)

    # Export Defense Brief PDF
    if state.pdf_path and os.path.exists(state.pdf_path):
        st.markdown("---")
        st.subheader("📥 Export Official Defense Brief")
        st.caption("Download the judge-ready defense brief generated during Phase 3 execution.")
        
        with open(state.pdf_path, "rb") as pdf_file:
            st.download_button(
                label="📄 Download Defense Brief (PDF)",
                data=pdf_file,
                file_name=os.path.basename(state.pdf_path),
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )