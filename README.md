````
# RepresentAI — AI-Powered Dispute & POD Defense

RepresentAI is a hybrid AI system designed to help detect potentially fraudulent or inconsistent delivery disputes using **Proof of Delivery (POD) documents, OCR, visual evidence, deterministic verification, and multimodal AI reasoning**.

The system is designed around a simple principle:

> **AI assists the investigation, while deterministic checks protect the final decision.**

---

## Problem

Delivery-related disputes can involve:

- Altered or manipulated Proof of Delivery documents
- Recipient name mismatches
- Invalid or suspicious tracking identifiers
- PODs that do not clearly support a delivered shipment
- Inconsistent visual or textual evidence

Manually reviewing every dispute is expensive and difficult to scale.

RepresentAI attempts to automate the initial investigation and route suspicious cases for appropriate action.

---

## Solution

RepresentAI uses a **hybrid deterministic + AI pipeline**:

```text
                 ┌──────────────────────┐
                 │   Dispute / POD      │
                 │   Image or Text      │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ OCR / Vision Layer   │
                 │ Text & Evidence      │
                 │ Extraction           │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Pre-Evaluation       │
                 │                      │
                 │ • Name similarity    │
                 │ • Tracking validation│
                 │ • Delivery status    │
                 │ • Visual/ELA signals  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Deterministic Gate   │
                 │                      │
                 │ Hard contradictions  │
                 │ override unsafe AI   │
                 │ conclusions          │
                 └──────────┬───────────┘
                            │
                   ┌────────┴─────────┐
                   │                  │
                   ▼                  ▼
             High confidence      Needs reasoning
             contradiction        / synthesis
                   │                  │
                   ▼                  ▼
                REVIEW /          Gemini
                REJECT            Auditor
                                      │
                                      ▼
                              Final Assessment
                                      │
                                      ▼
                           Defense Report / HITL
````

---

## Key Features

### 1. Multimodal POD Analysis

The system can process physical POD images and extract relevant evidence such as:

* Recipient/customer name
* Tracking number
* Delivery status
* Document text
* Visual anomalies

### 2. Deterministic Verification

Critical checks are performed using deterministic logic rather than relying entirely on an LLM:

* Recipient name similarity
* Tracking ID format validation
* Delivery-status validation
* Evidence consistency
* Image-forensic signals

This reduces the risk of an LLM producing an unsupported acceptance decision.

### 3. Fuzzy Name Matching

Recipient names are not always identical because of:

* OCR errors
* Abbreviations
* Minor spelling differences
* Formatting differences

The system therefore uses similarity-based matching instead of requiring exact string equality.

### 4. Image Forensic Signals

The pipeline uses Error Level Analysis (ELA) and visual evidence as supporting signals for possible document manipulation.

ELA is treated as a **forensic signal**, not as proof of fraud by itself.

### 5. Multimodal AI Reasoning

Gemini is used where semantic or visual reasoning is useful.

The deterministic layer acts as a safety boundary around the AI reasoning layer.

### 6. Human-in-the-Loop

Cases that cannot be safely resolved automatically can be routed for manual review rather than forcing an unreliable automated decision.

---

## Evaluation

The project contains two evaluation tracks.

### Programmatic Text Evaluation

34 deterministic text cases were evaluated.

**Result:**

* Accuracy: **100% (34/34)**

These cases primarily validate the correctness of the implemented business rules and should be considered a **software/logic validation benchmark**, not evidence of real-world fraud-detection accuracy.

### Physical POD Image Evaluation

16 multimodal image cases were evaluated using the available free-tier API resources.

**Result:**

| Metric       |                 Result |
| ------------ | ---------------------: |
| Accuracy     |             **93.75%** |
| Precision    |            **100.00%** |
| Recall       |             **88.89%** |
| F1 Score     |             **94.12%** |
| Mean Latency | **24.26 sec/document** |

The image benchmark contained both authentic and tampered POD examples.

One authentic unstructured document was incorrectly rejected because the extraction layer could not reliably recover the expected tracking/customer information.

This highlights an important limitation: **OCR/extraction quality directly affects downstream verification.**

---

## Engineering Constraints

The project was developed using free/open resources and therefore operates under API quota and latency constraints.

To make evaluation practical:

* Deterministic tests are executed without API calls.
* API calls are throttled during image evaluation.
* Failures and rate limits are handled separately from model reasoning errors.
* The system can fall back to deterministic/offline processing where appropriate.

The reported benchmarks should therefore be interpreted as **prototype evaluation results**, not production-scale performance claims.

---

## Razorpay Relevance

RepresentAI can act as an additional **dispute-risk and evidence-verification layer** in a payment/dispute workflow.

A possible production integration would be:

```text
Payment / Order
      │
      ▼
Delivery Evidence
      │
      ▼
RepresentAI
      │
      ├── Evidence Valid
      │       ↓
      │   Lower Risk
      │
      ├── Evidence Contradiction
      │       ↓
      │   High Risk / Review
      │
      └── Uncertain Evidence
              ↓
        Human Investigation
```

The system would not replace Razorpay's existing payment, fraud, logistics, or dispute infrastructure.

Instead, it could provide an additional **evidence intelligence layer** that helps prioritize disputes and reduce manual investigation effort.

For production deployment, the system would require:

* Real historical dispute data
* Properly labeled POD datasets
* Calibration on representative data
* Independent held-out evaluation
* Monitoring for OCR and model drift
* Secure API/data handling
* Integration with existing dispute and merchant systems

---

## Limitations

This is a prototype rather than a production fraud-detection system.

The main limitations are:

1. The evaluation dataset is relatively small.
2. Synthetic/programmatic cases are useful for testing logic but do not represent real-world distribution.
3. The ELA signal is heuristic and should be calibrated using a larger real dataset.
4. OCR errors can propagate into downstream verification.
5. Multimodal inference latency can be significant under free-tier API constraints.
6. Real production deployment would require larger held-out datasets and operational monitoring.

---

## Technology

* **Python**
* **Pydantic**
* **Pillow**
* **Google Gemini / Gemini Vision**
* **Tenacity**
* **OCR / image processing**
* **Deterministic rule engine**
* **Streamlit**
* **PDF report generation**

---

## Running the Project

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables in `.env`.

Run the evaluation:

```bash
python backend/evals/run_evals.py
```

Run the application:

```bash
streamlit run app.py
```

---

## Design Philosophy

RepresentAI does not attempt to make an LLM the sole decision-maker.

Instead:

**Extract → Verify → Gate → Reason → Review**

The goal is to combine the flexibility of multimodal AI with the predictability and auditability of deterministic verification.

---

## Project Status

**Hackathon Prototype — Functional**

The current system demonstrates:

* Multimodal POD analysis
* Deterministic evidence verification
* Fuzzy recipient matching
* Tracking validation
* Image-forensic signals
* AI-assisted reasoning
* Human-in-the-loop routing
* Automated evaluation and reporting

Further validation with real-world, held-out dispute data would be required before production deployment.
