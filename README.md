````markdown
# RepresentAI — Hybrid AI Dispute & Chargeback Defense System

> **A hybrid AI-powered dispute verification system that combines document intelligence, deterministic fraud checks, visual tampering detection, fuzzy identity matching, and LLM-assisted reasoning to evaluate Proof of Delivery (POD) evidence.**

---

## 1. Overview

RepresentAI is a prototype dispute-defense system designed around a common problem in digital commerce and payments:

> **How can a platform automatically evaluate whether a Proof of Delivery (POD) document genuinely supports a customer's delivery claim?**

In a traditional dispute workflow, evidence may need to be manually inspected for:

- Recipient/customer identity
- Delivery status
- Tracking number validity
- Document inconsistencies
- Possible image manipulation
- Suspicious formatting or typography
- Contradictions between the evidence and transaction/ledger data

RepresentAI attempts to automate this initial verification process.

The system accepts structured or unstructured evidence such as:

- POD images
- Delivery receipts
- Courier documents
- Text-based delivery records

It extracts relevant information, evaluates forensic and business signals, applies deterministic safety checks, and produces a final dispute recommendation.

The system supports three primary outcomes:

- `ACCEPTED` — Evidence sufficiently supports fulfillment.
- `REJECTED` — Evidence contains strong contradictory or suspicious signals.
- `REVIEW` — Evidence cannot be safely resolved automatically and should be escalated to a human reviewer.

---

# 2. Problem Statement

Chargeback and dispute handling requires a payment platform to determine whether a merchant's evidence actually proves fulfillment.

A submitted POD may appear legitimate while containing problems such as:

- Incorrect recipient name
- Slightly modified recipient names
- Invalid tracking identifiers
- Non-delivery statuses
- Edited images
- Font inconsistencies
- Contradictory delivery information
- Missing or poorly structured information

A purely rule-based system can be predictable but may struggle with unstructured evidence.

A purely LLM-based system can understand unstructured documents but introduces problems such as:

- Hallucination
- Inconsistent reasoning
- Lack of deterministic guarantees
- API failures
- Rate limits
- Difficulty reproducing decisions

RepresentAI therefore uses a **hybrid architecture**.

---

# 3. Core Design Philosophy

The central design principle is:

```text
Use AI for understanding.
Use deterministic logic for safety-critical decisions.
Use human review when confidence is insufficient.
````

Instead of allowing an LLM to independently decide every dispute, the system combines:

1. Document/OCR extraction
2. Forensic analysis
3. Deterministic validation
4. Fuzzy identity matching
5. LLM-assisted reasoning
6. Final safety/consistency checks
7. Human-in-the-loop escalation

This provides a more controlled architecture for a fintech/dispute environment.

---

# 4. High-Level Architecture

```text
                         ┌───────────────────────┐
                         │     User / Merchant   │
                         │   Uploads Evidence    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      Input Layer      │
                         │                       │
                         │  • POD Image          │
                         │  • Text Evidence      │
                         │  • Case / Ledger Data │
                         └───────────┬───────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │       Evidence Extraction       │
                    │                                 │
                    │  OCR / Vision / Text Parsing    │
                    │  • Customer Name                │
                    │  • Tracking ID                  │
                    │  • Delivery Status              │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │       Pre-Evaluation Layer       │
                    │                                 │
                    │  • Name Similarity              │
                    │  • Tracking Validation          │
                    │  • Delivery Status              │
                    │  • ELA / Image Signals         │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │    Deterministic Safety Gate     │
                    │                                 │
                    │  Hard contradictions / rules    │
                    │  are checked before final       │
                    │  acceptance.                    │
                    └───────────────┬─────────────────┘
                                    │
                       ┌────────────┴─────────────┐
                       │                          │
                 Hard contradiction?              │
                       │                          │
                 ┌─────▼─────┐                    │
                 │ REJECT /  │                    │
                 │  REVIEW   │                    │
                 └───────────┘                    │
                                                  ▼
                                  ┌─────────────────────────┐
                                  │   Gemini LLM Auditor    │
                                  │                         │
                                  │ Contextual reasoning +   │
                                  │ evidence explanation    │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │  Post-LLM Guardrails    │
                                  │                         │
                                  │ Re-check critical rules │
                                  │ before final verdict    │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │      Final Decision      │
                                  │                         │
                                  │ ACCEPTED / REJECTED /   │
                                  │ REVIEW                  │
                                  └────────────┬────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │   Defense / Audit Brief  │
                                  │                         │
                                  │ • Verdict                │
                                  │ • Confidence             │
                                  │ • Evidence signals       │
                                  │ • Audit explanation      │
                                  └─────────────────────────┘
```

---

# 5. Main Components

## 5.1 OCR / Evidence Extraction

The system extracts structured information from submitted evidence.

Important fields include:

* Recipient/customer name
* Tracking number
* Delivery status
* Relevant document information

For images, the system can use the multimodal model for extraction.

For text-based evidence, deterministic parsing and regular expressions are available.

The implementation also contains caching mechanisms to reduce unnecessary API calls during development and evaluation.

---

# 6. Pre-Evaluation Engine

Before the final decision, the evidence is converted into measurable signals.

The system currently evaluates signals such as:

### Recipient Name Similarity

The extracted recipient name is compared with the expected customer name using fuzzy string matching.

This allows the system to handle cases such as:

```text
Expected:
Rahul Sharma

Evidence:
Rahul Sharm
```

rather than requiring exact string equality.

---

### Tracking ID Validation

Tracking identifiers are checked against the expected format.

Malformed or invalid identifiers can become a deterministic rejection/review signal.

---

### Delivery Status

The system checks whether the evidence actually indicates fulfillment.

Examples of suspicious/non-fulfillment states include:

```text
Cancelled
Failed
Returned
Undelivered
Attempted
```

The exact business rules are implemented in the evaluation/auditor logic.

---

### Image Forensics / ELA

The system also uses image-level forensic signals such as Error Level Analysis (ELA).

ELA is used as an additional signal for potential image manipulation.

It is important to note that ELA is treated as a **forensic signal rather than absolute proof of manipulation**.

---

# 7. Hybrid Decision Architecture

RepresentAI intentionally does not rely on the LLM alone.

The architecture separates:

```text
Extraction
     ↓
Measurement
     ↓
Deterministic validation
     ↓
LLM contextual reasoning
     ↓
Safety guardrails
     ↓
Final decision
```

This provides two complementary capabilities.

### Deterministic Layer

Useful for:

* Tracking format validation
* Hard contradictions
* Delivery-status checks
* Name similarity thresholds
* Repeatable benchmark evaluation
* Safety constraints

### AI Layer

Useful for:

* Understanding unstructured documents
* Interpreting visual evidence
* Combining multiple signals
* Generating human-readable reasoning
* Handling evidence that does not fit a simple rule

---

# 8. LLM Auditor

The project uses Google's Gemini multimodal model for the AI-assisted auditing stage.

The LLM receives contextual information including:

* Ledger/case information
* Extracted evidence
* Pre-evaluation metrics
* Forensic signals
* Business rules

The LLM is not treated as an unrestricted final authority.

Critical conditions are checked by deterministic guardrails around the model.

---

# 9. API Failure Handling

A major development constraint for this project was limited access to API resources and rate limits.

Instead of allowing an API failure to crash the evaluation pipeline, the system includes failure handling and retry mechanisms.

The architecture supports:

```text
API Request
    ↓
Rate Limit / Temporary Failure?
    │
    ├── No → Continue
    │
    └── Yes
          ↓
       Retry with
     exponential backoff
          ↓
     Still failing?
          ↓
      REVIEW / FALLBACK
```

This is important because infrastructure availability should not be incorrectly reported as model reasoning failure.

The benchmark system therefore distinguishes between:

* Model correctness
* Model incorrectness
* Infrastructure/API failure

where applicable.

---

# 10. Offline / Deterministic Evaluation Mode

A major part of the project is the offline evaluation mode.

The offline mode exists because repeatedly calling a paid or rate-limited multimodal API for every benchmark case is impractical during development.

The offline engine allows:

* Deterministic testing
* Reproducible evaluation
* Zero API cost
* Rapid iteration
* Regression testing

This mode should **not** be interpreted as equivalent to the multimodal LLM itself.

Instead:

```text
Offline Mode
= deterministic system / rule-engine testing

Live Mode
= OCR/Vision + LLM-assisted evaluation
```

This distinction is intentionally maintained to avoid presenting deterministic benchmark results as LLM accuracy.

---

# 11. Evaluation Strategy

The project contains multiple evaluation tracks.

## Track 1 — Programmatic Text Evaluation

The current benchmark contains:

```text
34 text cases
```

covering accepted and rejected evidence.

Latest result:

```text
Total Cases: 34
Correct:     34
Accuracy:    100.00%
```

This benchmark is primarily useful for testing deterministic business logic and regression behavior.

It should not be interpreted as proof of general-world accuracy.

---

# 12. Track 2 — Multimodal Vision Benchmark

The project also evaluates physical/unstructured POD images.

Latest benchmark:

```text
Total Images Tested : 16

Accuracy            : 93.75%
Precision           : 100.00%
Recall              : 88.89%
F1 Score            : 94.12%

Mean Latency        : 24.26 seconds/document
```

The result corresponds to:

```text
15 correct
1 incorrect
```

The incorrect case was:

```text
Unstructured data image 2.png
```

The system predicted:

```text
REJECTED
```

while the expected result was:

```text
ACCEPTED
```

The system reported:

```text
Name Mismatch
Invalid Tracking ID
```

This demonstrates an important limitation of the current system:

> A strict deterministic gate can sometimes reject legitimate evidence when OCR/extraction is incomplete or unreliable.

This is one of the areas that would require improvement before production deployment.

---

# 13. Why Precision and Recall Both Matter

For a dispute-defense system, accuracy alone is not sufficient.

Two types of mistakes are especially important.

### False Positive

A legitimate claim is incorrectly treated as suspicious.

This can cause:

* Customer friction
* Merchant disputes
* Incorrect claim rejection
* Poor user experience

### False Negative

Fraudulent or invalid evidence is incorrectly accepted.

This can cause:

* Financial loss
* Incorrect chargeback decisions
* Increased fraud exposure

Therefore the system tracks:

```text
Accuracy
Precision
Recall
F1 Score
False Acceptance Rate
False Rejection Rate
```

The objective is not simply to maximize accuracy.

The objective is to find a useful balance between:

```text
Fraud prevention
+
Customer fairness
+
Operational efficiency
```

---

# 14. Ablation Testing

The repository contains an ablation evaluation script to understand the contribution of individual features.

Example results from the development benchmark:

| Configuration            | Accuracy | Precision | Recall |   FAR |
| ------------------------ | -------: | --------: | -----: | ----: |
| Full Hybrid Pipeline     |    82.0% |    100.0% |  77.5% |  0.0% |
| No ELA Analysis          |    82.0% |    100.0% |  77.5% |  0.0% |
| No Fuzzy Matching        |    42.0% |    100.0% |  27.5% |  0.0% |
| No Tracking Format Check |    90.0% |     88.9% | 100.0% | 50.0% |

These numbers are useful primarily for understanding system behavior on the current benchmark.

One important observation is the effect of fuzzy matching.

Removing fuzzy matching caused a significant reduction in recall:

```text
Full Pipeline Recall:      77.5%
Without Fuzzy Matching:    27.5%
```

This indicates that exact string matching is insufficient for recipient-name variations in the tested cases.

Similarly, removing tracking validation dramatically increased the False Acceptance Rate:

```text
Without Tracking Check FAR: 50%
```

This supports the role of deterministic validation as a safety mechanism.

---

# 15. Dataset Structure

The repository contains synthetic and adversarial evaluation assets.

Example structure:

```text
represent-ai/
│
├── backend/
│   ├── evals/
│   │   ├── benchmark_metrics.py
│   │   ├── benchmark_runner.py
│   │   ├── eval_dataset.py
│   │   ├── generate_image_dataset.py
│   │   ├── run_ablation.py
│   │   ├── run_evals.py
│   │   └── test_pipeline_eval.py
│   │
│   ├── auditor_agent.py
│   ├── confidence_scorer.py
│   ├── database.py
│   ├── main.py
│   ├── ocr_engine.py
│   ├── orchestrator.py
│   ├── pdf_generator.py
│   ├── pre_evaluator.py
│   └── state.py
│
├── evals/
│   └── synthetic_images/
│       └── dev_200/
│           ├── authentic/
│           ├── tampered/
│           └── metadata.json
│
├── frontend/
│   └── app.py
│
├── tests/
│   ├── fixtures/
│   │   └── adversarial_dataset/
│   │       ├── dev_200/
│   │       └── held_out_100/
│   │
│   └── test_pipeline.py
│
├── init_db.py
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 16. Development vs Held-Out Evaluation

The repository distinguishes between development/adversarial data and held-out data.

The intended evaluation methodology is:

```text
Development / Calibration Data
            ↓
     Tune thresholds
            ↓
      Freeze system
            ↓
      Held-Out Dataset
            ↓
     Final evaluation
```

The held-out dataset should not be used repeatedly for tuning thresholds.

This prevents benchmark leakage and gives a more realistic estimate of generalization.

---

# 17. Important Dataset Limitation

This project was developed under practical student-level constraints, including:

* Limited API quotas
* Free-tier API usage
* Limited compute resources
* Limited access to large real-world dispute datasets
* Limited development time

Therefore the current benchmark should **not** be presented as representative of millions of real-world disputes.

The current dataset is best viewed as:

```text
A prototype validation benchmark
```

rather than:

```text
A production-scale fraud dataset
```

A production deployment would require a much larger and more diverse dataset containing real-world variations.

---

# 18. Adversarial Testing

The project includes adversarial test fixtures designed to challenge the pipeline.

The purpose is to test cases such as:

* Modified recipient names
* Malformed tracking IDs
* Non-delivery statuses
* Image manipulation
* Unstructured documents
* OCR ambiguity
* Conflicting evidence

The goal is not to prove that the system detects every possible attack.

Instead, adversarial testing is used to identify weaknesses before deployment.

---

# 19. Confidence Scoring

The system also exposes confidence information alongside the verdict.

Example:

```text
Verdict: REJECTED
Confidence: 0.98
```

Confidence should be interpreted as a system-level decision signal rather than a calibrated probability of fraud.

For production use, confidence scores should be calibrated against a large labeled validation dataset.

---

# 20. Human-in-the-Loop Design

Not every dispute should be automatically resolved.

The system therefore supports a `REVIEW` pathway.

Conceptually:

```text
                Evidence
                   │
                   ▼
             Automated Audit
                   │
          ┌────────┼────────┐
          │        │        │
          ▼        ▼        ▼
       ACCEPTED  REJECTED  REVIEW
                              │
                              ▼
                     Human Investigator
```

Cases can be routed for human review when:

* Evidence is ambiguous
* OCR is unreliable
* API infrastructure fails
* Signals contradict each other
* Confidence is insufficient
* A hard decision cannot safely be made automatically

This is particularly important for financial systems because an automated system should not be forced to make a binary decision when evidence quality is poor.

---

# 21. Generated Defense Brief

The system can generate an audit/defense PDF containing information useful to a reviewer.

Example output:

```text
Official_Defense_Brief_<tracking_id>.pdf
```

The report can contain:

* Case information
* Evidence information
* Extracted fields
* Forensic signals
* Decision
* Confidence
* Reasoning

This creates an auditable artifact instead of only returning a raw model response.

---

# 22. Database Layer

The project contains a SQLite database layer for storing application-level information.

Current development setup uses:

```text
SQLite
```

This keeps the prototype lightweight and avoids external infrastructure requirements.

A production implementation could replace this with a scalable transactional database.

---

# 23. Frontend

The project includes a Streamlit-based frontend.

The intended workflow is:

```text
Upload Evidence
       ↓
Process Case
       ↓
Extract Evidence
       ↓
Run Verification
       ↓
Display Verdict
       ↓
Show Supporting Signals
       ↓
Generate Defense Brief
```

The UI is intended to make the system understandable to a human reviewer rather than exposing internal Python execution details.

---

# 24. Error Handling

The system is designed to avoid treating infrastructure failures as model failures.

Potential infrastructure failures include:

* API rate limits
* Temporary API errors
* Timeouts
* Missing API keys
* Network errors

The system can retry temporary failures and route unresolved failures toward a safer fallback/review path.

This is especially important when using free-tier APIs during development.

---

# 25. Caching

The project contains cache mechanisms for expensive API operations.

Examples include:

```text
.llm_cache/
.ocr_cache/
```

Caching helps:

* Reduce repeated API calls
* Reduce development cost
* Improve iteration speed
* Avoid unnecessary quota consumption
* Make local testing more practical

These cache directories should not contain secrets and should be excluded from version control where appropriate.

---

# 26. Security Considerations

The project is a prototype and should not be considered production-ready security infrastructure.

Important production considerations would include:

* Secure API-key management
* Encryption of uploaded evidence
* Access control
* Audit logging
* Data retention policies
* PII protection
* Secure object storage
* Rate limiting
* Malware scanning for uploads
* Authentication and authorization
* Secure database configuration

API credentials should never be committed to Git.

The `.env` file should remain private.

---

# 27. Technology Stack

## Backend

* Python
* Pydantic
* Google Gemini API
* PIL / Pillow
* SQLite
* Tenacity
* Regular expressions
* Fuzzy string similarity

## Frontend

* Streamlit

## Evaluation

* Custom benchmark runners
* Programmatic test cases
* Synthetic POD images
* Adversarial fixtures
* Ablation testing

## Output

* PDF audit / defense briefs

---

# 28. Project Structure Explained

### `backend/orchestrator.py`

Coordinates the complete dispute-processing pipeline.

It connects:

```text
Input
→ Extraction
→ Pre-evaluation
→ Audit
→ Final decision
→ Report generation
```

---

### `backend/pre_evaluator.py`

Calculates pre-evaluation metrics such as:

* Name similarity
* ELA-related signals
* Tracking validation
* Other evidence-level checks

---

### `backend/auditor_agent.py`

Contains the AI-assisted auditing logic and deterministic fallback/auditing mechanisms.

The auditor combines case information with extracted evidence and applies the defined decision rules.

---

### `backend/ocr_engine.py`

Responsible for extracting information from uploaded evidence.

---

### `backend/confidence_scorer.py`

Handles confidence-related calculations used by the application.

---

### `backend/state.py`

Maintains structured pipeline state between processing stages.

---

### `backend/pdf_generator.py`

Generates the final defense/audit document.

---

### `backend/database.py`

Provides database functionality for the application.

---

### `backend/evals/benchmark_runner.py`

Calculates benchmark metrics such as:

* TP
* TN
* FP
* FN
* Accuracy
* Precision
* Recall
* F1
* FAR
* FRR

---

### `backend/evals/run_ablation.py`

Evaluates how system performance changes when individual components are removed.

---

### `backend/evals/run_evals.py`

Runs the project's evaluation suites.

---

# 29. Installation

Clone the repository:

```bash
git clone <repository-url>
cd represent-ai
```

Create a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 30. Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

Do not commit the `.env` file.

The project should be configured so that missing or unavailable API credentials do not expose the secret or crash the complete evaluation workflow.

---

# 31. Running the Application

Start the Streamlit application using:

```bash
streamlit run frontend/app.py
```

The browser interface should then provide the evidence-processing workflow.

---

# 32. Running the Evaluation

Run the evaluation suite:

```bash
python backend/evals/run_evals.py
```

The evaluation script reports the performance of the available benchmark tracks.

For example:

```text
TRACK 1: PROGRAMMATIC TEXT EVALUATION

Track 1 Accuracy: 100.00%
Total Text Cases: 34
```

and:

```text
TRACK 2: MULTIMODAL VISION BENCHMARK

Total Images Tested : 16
Overall Accuracy    : 93.75%
Precision           : 100.00%
Recall              : 88.89%
F1 Score            : 94.12%
Mean Latency        : 24.26s / document
```

---

# 33. Running Ablation Tests

Run:

```bash
python backend/evals/run_ablation.py
```

This evaluates the effect of removing individual components from the pipeline.

---

# 34. Running the Benchmark Metrics

Run:

```bash
python backend/evals/benchmark_runner.py
```

This produces detailed classification metrics including:

```text
TP
TN
FP
FN
Accuracy
Precision
Recall
F1
False Acceptance Rate
False Rejection Rate
```

---

# 35. Example Decision

A simplified example:

```text
Customer:
Rahul Sharma

Extracted Recipient:
Rahul Sharma

Tracking ID:
TRK-9082-X

Delivery Status:
DELIVERED

Name Similarity:
1.00

ELA Signal:
Low

Tracking Format:
Valid

Final Verdict:
ACCEPTED
```

Another example:

```text
Customer:
Rahul Sharma

Extracted Recipient:
John Fake Person

Tracking ID:
INVALID

Delivery Status:
DELIVERED

Name Similarity:
0.00

Visual Tampering:
Detected

Final Verdict:
REJECTED
```

---

# 36. Why This Architecture Is Relevant to Razorpay

The architecture is designed around a problem relevant to payment disputes:

```text
Payment / Transaction
        │
        ▼
      Dispute
        │
        ▼
 Merchant Evidence
        │
        ▼
 RepresentAI
        │
        ├── Evidence Extraction
        ├── Document Verification
        ├── Identity Matching
        ├── Tracking Validation
        ├── Tampering Detection
        ├── AI Reasoning
        └── Risk Decision
        │
        ▼
 ACCEPTED / REJECTED / REVIEW
```

In a larger payment platform, such a system could potentially operate as an evidence pre-screening layer.

For example:

```text
Low-risk / strong evidence
        ↓
Automated processing

High-risk / contradictory evidence
        ↓
Enhanced investigation

Ambiguous evidence
        ↓
Human review
```

This could reduce the amount of repetitive manual verification required by dispute operations teams.

---

# 37. Potential Production Integration

A production-grade implementation could integrate with:

```text
Payment Transaction Data
        +
Merchant Information
        +
Customer Information
        +
Courier / Logistics Data
        +
Submitted Evidence
        ↓
Dispute Verification Engine
```

Additional signals could include:

* Transaction history
* Merchant risk score
* Courier API confirmation
* Delivery timestamp
* GPS/geolocation metadata
* Device metadata
* Historical dispute patterns
* Merchant-specific evidence reliability
* Image/document provenance
* Previous claims involving the same tracking ID

These signals are not all implemented in the current prototype.

They represent possible future production integrations.

---

# 38. Current Limitations

The current implementation has several limitations.

### 1. Dataset Size

The current multimodal benchmark is small.

Only:

```text
16 physical/unstructured image cases
```

were used in the latest live vision evaluation.

Therefore, the reported 93.75% accuracy should not be interpreted as production-scale performance.

---

### 2. Synthetic Data

A significant portion of the development benchmark is programmatically generated.

Synthetic benchmarks are useful for:

* Regression testing
* Unit testing
* Controlled experiments
* Feature ablation

However, they do not fully represent real-world document diversity.

---

### 3. OCR Errors

Incorrect OCR can propagate into later stages.

For example:

```text
Image
 ↓
Incorrect OCR
 ↓
Incorrect tracking ID
 ↓
Deterministic rejection
```

This is visible in the current false-negative case.

---

### 4. ELA Limitations

ELA is not a definitive proof of manipulation.

Compression, resizing, screenshots, and other image transformations can affect forensic signals.

Therefore ELA should be treated as one feature among several.

---

### 5. API Dependency

The multimodal evaluation depends on an external LLM API.

Free-tier rate limits can significantly increase latency.

The project therefore contains offline evaluation and caching mechanisms.

---

### 6. Confidence Calibration

Current confidence values should not be interpreted as statistically calibrated fraud probabilities.

Calibration would require a significantly larger labeled validation dataset.

---

# 39. Future Improvements

The most important improvements for a production-grade version would be:

## 39.1 Larger Held-Out Dataset

Build a substantially larger dataset containing:

* Realistic POD layouts
* Different courier formats
* Different fonts
* Different image qualities
* Different lighting conditions
* Screenshots
* Scanned documents
* Partial documents
* OCR corruption
* Legitimate name variations
* Sophisticated tampering

---

## 39.2 Statistical Calibration

Instead of relying exclusively on manually selected forensic thresholds, estimate thresholds from development data.

For example:

```text
Clean Images
     ↓
ELA Distribution
     ↓
Mean / Standard Deviation / Percentiles
     ↓
Threshold Calibration
```

The final threshold should then be frozen before evaluation on the held-out set.

---

## 39.3 Better OCR Confidence Handling

Instead of treating extracted values as always correct:

```text
OCR Result
   ↓
OCR Confidence
   ↓
High confidence → Continue
Low confidence  → REVIEW / Secondary extraction
```

---

## 39.4 Multi-Signal Evidence Fusion

Combine:

```text
Identity
+
Tracking
+
Delivery status
+
Visual forensics
+
Document consistency
+
External verification
```

rather than relying heavily on any single feature.

---

## 39.5 Human Review Feedback Loop

Human decisions could eventually be used to improve the system.

```text
Automated Decision
       ↓
Human Review
       ↓
Corrected Decision
       ↓
Labeled Dataset
       ↓
Threshold / Model Improvement
```

This creates a continuous improvement loop.

---

# 40. Ethical and Operational Principle

The goal of RepresentAI is not to blindly automate dispute rejection.

The goal is:

> **Automate high-confidence evidence verification while routing uncertain cases to humans.**

This distinction is important in financial systems.

An automated system should minimize both:

```text
Fraud leakage
```

and

```text
Incorrect rejection of legitimate customers/merchants
```

---

# 41. Benchmark Interpretation

The current benchmark demonstrates that the system is capable of:

* Deterministic evidence validation
* Fuzzy recipient matching
* Tracking ID validation
* Delivery-status validation
* Image-based evidence analysis
* Visual tampering signal detection
* LLM-assisted reasoning
* Ablation testing
* Offline evaluation
* API failure handling
* Human-review routing
* Audit report generation

However, the benchmark does **not** establish that the system is production-ready or that it will maintain the same performance on large real-world datasets.

The current results should therefore be interpreted as:

> **Prototype-level evidence that the architecture and individual components work on the available evaluation data.**

---

# 42. Key Results

### Programmatic Text Benchmark

```text
Cases:       34
Correct:     34
Accuracy:    100.00%
```

### Multimodal Vision Benchmark

```text
Cases:       16
Correct:     15
Accuracy:    93.75%

Precision:   100.00%
Recall:       88.89%
F1:           94.12%

Mean Latency:
24.26 seconds/document
```

### Ablation Benchmark

The development ablation study demonstrated that:

```text
Fuzzy matching
```

and

```text
Tracking validation
```

have significant effects on the tested benchmark.

These results are used to justify the inclusion of these components in the hybrid architecture.

---

# 43. Project Philosophy

RepresentAI follows a simple principle:

```text
                    ┌──────────────────────┐
                    │       AI             │
                    │ Understand Evidence  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Deterministic     │
                    │       Rules          │
                    │ Verify Constraints   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Human          │
                    │ Review Uncertainty   │
                    └──────────────────────┘
```

The objective is not to replace human investigators completely.

The objective is to make them faster and provide them with structured, explainable evidence.

---

# 44. Disclaimer

RepresentAI is a student-built prototype developed for a hackathon.

It is not intended to make unsupervised real-world financial, legal, or customer-account decisions without appropriate validation, monitoring, security controls, and human oversight.

The reported benchmark results are specific to the datasets and evaluation conditions used during development.

They should not be interpreted as guaranteed performance on real-world production data.

---

# 45. Author

Built as a student project for the Razorpay hackathon.

The project focuses on applying:

* Artificial Intelligence
* Multimodal document understanding
* Computer vision
* Forensic analysis
* Deterministic risk rules
* Human-in-the-loop decision systems
* Evaluation-driven engineering

to the problem of payment dispute and chargeback evidence verification.

---

# 46. Final Summary

RepresentAI is a **Hybrid Deterministic-Gated Agentic Pipeline** for evaluating Proof of Delivery evidence.

Its architecture combines:

```text
                 POD / Evidence
                       │
                       ▼
                 OCR / Vision
                       │
                       ▼
              Pre-Evaluation
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
  Name Matching   Tracking Check    Image Forensics
       │               │                │
       └───────────────┼────────────────┘
                       ▼
              Deterministic Gate
                       │
                       ▼
                Gemini Auditor
                       │
                       ▼
              Safety Guardrails
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          ACCEPTED  REJECTED   REVIEW
                       │
                       ▼
               Defense / Audit PDF
```

The current prototype demonstrates a working end-to-end system with:

* Deterministic validation
* Multimodal evidence analysis
* Fuzzy identity matching
* Image tampering signals
* LLM-assisted reasoning
* API failure handling
* Offline evaluation
* Ablation testing
* Human-in-the-loop escalation
* Audit report generation

The next stage toward production would require substantially larger real-world datasets, statistical calibration, stronger OCR confidence handling, external logistics verification, security hardening, latency optimization, and extensive held-out evaluation.

---

```
```
