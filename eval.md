# Phase-Wise Evaluation Framework: Mutual Fund FAQ Assistant

This document defines the evaluation criteria, test metrics, and verification steps for each phase of the implementation plan, ensuring complete alignment with safety, accuracy, and compliance benchmarks.

---

## Phase 1: Data Ingestion & Corpus Parsing
* **Focus:** Evaluating document parser purity and text encoding validity.

### 1. Verification Benchmarks
| Metric | Measurement Methodology | Target Threshold |
| :--- | :--- | :--- |
| **Ingestion Coverage** | Verify all 5 whitelisted schemes have generated raw file maps inside `backend/data/raw/`. | 100% (5/5 files) |
| **Boilerplate Purity** | Scan raw files for navigational keywords (e.g., *"Demat Account"*, *"F&O"*). | 0 matches |
| **Chunk Count Verification** | Audit total chunk payloads stored in `backend/data/vector_store.json`. | $\ge 1$ chunk per scheme |

### 2. Manual Inspection Checklist
- [ ] Confirm no raw HTML tags (`<div>`, `<script>`, etc.) exist in the chunk outputs.
- [ ] Verify metadata schemas map the exact scheme names and corresponding whitelisted Groww URLs.

---

## Phase 2: Hybrid Search & Retrieval System
* **Focus:** Measuring search relevance, dense BGE embedding accuracy, and Reciprocal Rank Fusion (RRF).

### 1. Retrieval Quality Metrics
- **Hit Rate @ 2:** For 10 sample queries (2 per scheme), verify that the top 2 retrieved chunks correspond to the target scheme. (Target: **100%**)
- **Mean Reciprocal Rank (MRR):** Measures the rank position of the first relevant chunk returned.
  $$MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{rank_i}$$
  (Target: **$\ge 0.85$**)

### 2. Hybrid Search Edge Checks
- [ ] **Keyword matches (BM25):** Querying specialized metrics (e.g., *"TER"*, *"lock-in"*) must return paragraphs containing these specific strings.
- [ ] **Semantic matches (BGE):** Querying with spelling errors or synonyms (e.g., *"charge to switch"* for exit load) must rank the correct load paragraph within the top 2 slots.

---

## Phase 3: Guardrails & Orchestrator Execution
* **Focus:** Asserting input-output safety thresholds, PII detection, and compliance rejections.

### 1. Guardrail Confusion Matrix
We verify input classifications against a test matrix containing 20 safe queries and 20 unsafe queries (PII or advisory).

| Metric | Target Threshold | Description |
| :--- | :--- | :--- |
| **PII False Negative Rate (FNR)** | **0%** | Critical: No query containing a valid PAN, Aadhaar, phone, or bank account must pass to the LLM. |
| **Advisory False Negative Rate (FNR)** | **0%** | Critical: No advisory or rating comparison query must generate a factual answer. |
| **Safe False Positive Rate (FPR)** | **$\le 10\%$** | Acceptable rate of rejecting valid factual queries to err on the side of safety. |

### 2. Formatting Validator Verification
- **Output Length Constraint:** Programmatic assert that no return payload contains $>3$ sentences. (Target: **100%**)
- **Citation Whitelisting:** Scan the response's citation URL to confirm it belongs exactly to the 5 whitelisted Groww URLs. (Target: **100%**)

---

## Phase 4: API & Front-End Interface
* **Focus:** Response latency, REST payload structures, and design compliance.

### 1. Performance Metrics
- **API Response Latency:** Measured from query input to response layout presentation on the frontend.
  - Target: **$\le 1500\text{ ms}$** (Normal API response state)
  - Target: **$\le 150\text{ ms}$** (Guardrail/PII block response state)
- **API Stability:** Percentage of requests returning HTTP status `200 OK` under concurrent requests. (Target: **99.9%**)

### 2. UI Layout Inspection
- [ ] **Disclaimer Visibility:** Confirm the warning banner *"Facts-only. No investment advice."* is sticky, prominent, and visible without scrolling.
- [ ] **Interactive Suggesters:** Clicking any chip bubble triggers immediate execution without UI lag or multiple overlapping text loads.
- [ ] **Input Field Deactivation:** Confirm the user input field and submit button are locked/disabled during loading to block duplicate requests.

---

## Phase 5: Verification Suite & Final Compliance Audit
* **Focus:** Complete end-to-end regression evaluation checks.

### 1. Verification Test cases (`evaluate.py`)
Run the test command (`python -m backend.scripts.evaluate`) to ensure all check gates evaluate to `[PASS]`:

```bash
python -m backend.scripts.evaluate
```

### 2. Final Compliance Checklist
- [ ] Zero storage of customer identifiers (PAN, Aadhaar, account numbers).
- [ ] Every response ends with the whitelisted Groww source URL.
- [ ] Every response includes a timestamp footer: `Last updated from sources: <date>`.
