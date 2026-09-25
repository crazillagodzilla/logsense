#do not run this script directly, it is meant to be run in a Google Colab environment with mounted Google Drive for data access.
"""
%%writefile experiment_runner.py
import os
import re
import joblib
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

# Google Drive storage paths
DATA_DIR = "/content/drive/MyDrive"
LOG_PATH = os.path.join(DATA_DIR, "HDFS.log")
LABEL_PATH = os.path.join(DATA_DIR, "anomaly_label.csv")

# 1. Scaled sample size (500,000 log lines)
MAX_LINES = 500000

def parse_logs():
    print(f"1. Loading scaled HDFS log sample ({MAX_LINES:,} lines) from '{LOG_PATH}'...")
    if not os.path.exists(LOG_PATH):
        raise FileNotFoundError(
            f"❌ File not found at '{LOG_PATH}'. Ensure Google Drive is mounted and DATA_DIR is correct."
        )

    log_lines = []
    with open(LOG_PATH, "r") as f:
        for i in range(MAX_LINES):
            line = f.readline()
            if not line:
                break
            log_lines.append(line.strip())

    print(f"2. Parsing {len(log_lines):,} lines with Drain3...")
    config = TemplateMinerConfig()
    template_miner = TemplateMiner(config=config)

    block_ids = []
    template_ids = []
    block_regex = re.compile(r"(blk_-?\d+)")

    for line in log_lines:
        match = block_regex.search(line)
        block_id = match.group(1) if match else "UNKNOWN"
        result = template_miner.add_log_message(line)
        template_id = f"E{result['cluster_id']}"

        block_ids.append(block_id)
        template_ids.append(template_id)

    df_logs = pd.DataFrame({"BlockId": block_ids, "TemplateId": template_ids})
    df_logs = df_logs[df_logs["BlockId"] != "UNKNOWN"]

    print("3. Aggregating block sequence strings & extracting structural metadata...")
    # Compute template string + sequence length + unique template count per block
    df_blocks = df_logs.groupby("BlockId").agg(
        TemplateId=("TemplateId", lambda x: " ".join(x)),
        seq_len=("TemplateId", "count"),
        unique_templates=("TemplateId", "nunique")
    ).reset_index()

    if not os.path.exists(LABEL_PATH):
        raise FileNotFoundError(f"❌ File not found at '{LABEL_PATH}'.")

    df_labels = pd.read_csv(LABEL_PATH)
    df_labels["true_label"] = df_labels["Label"].apply(lambda x: 1 if x == "Anomaly" else 0)

    eval_df = pd.merge(df_blocks, df_labels, on="BlockId", how="inner")
    print(f"   Evaluated blocks: {len(eval_df):,} | Anomalies: {eval_df['true_label'].sum():,}")

    return template_miner, eval_df

def run_grid_search(eval_df):
    print("4. Running feature-stacked experimentation grid search...\n")

    # Standardize numerical structural metadata features
    scaler = StandardScaler()
    X_meta = scaler.fit_transform(eval_df[["seq_len", "unique_templates"]])

    vectorizer_configs = [
        {"name": "TFIDF-Unigram", "ngram_range": (1, 1)},
        {"name": "TFIDF-Bigram", "ngram_range": (1, 2)},
        {"name": "TFIDF-Trigram", "ngram_range": (1, 3)},
    ]

    results = []
    best_f1 = -1.0
    best_artifacts = {}

    for v_cfg in vectorizer_configs:
        vectorizer = TfidfVectorizer(
            token_pattern=r"\b[eE]\d+\b",
            lowercase=False,
            ngram_range=v_cfg["ngram_range"],
            sublinear_tf=True
        )
        X_tfidf = vectorizer.fit_transform(eval_df["TemplateId"])

        # 2. Combine sparse TF-IDF text features with scaled structural metadata
        X_combined = sp.hstack([X_tfidf, X_meta], format="csr")

        # Isolation Forest Grid
        for contamination in [0.015, 0.02, 0.025, 0.03, 0.035]:
            clf = IsolationForest(
                n_estimators=250,
                max_features=0.85,
                contamination=contamination,
                random_state=42,
                n_jobs=-1
            )
            preds_raw = clf.fit_predict(X_combined)
            preds = [1 if p == -1 else 0 for p in preds_raw]

            p = precision_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
            r = recall_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
            f1 = f1_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
            acc = accuracy_score(eval_df["true_label"], preds)

            results.append({
                "Model": "IsolationForest",
                "Vectorizer": v_cfg["name"],
                "Param": f"cont={contamination}",
                "Precision": round(p, 4),
                "Recall": round(r, 4),
                "F1-Score": round(f1, 4),
                "Accuracy": round(acc, 4)
            })

            if f1 > best_f1:
                best_f1 = f1
                best_artifacts = {
                    "vectorizer": vectorizer,
                    "scaler": scaler,
                    "model": clf
                }

        # One-Class SVM Grid
        for nu in [0.015, 0.02, 0.025, 0.03]:
            for kernel in ["rbf", "linear"]:
                clf = OneClassSVM(kernel=kernel, nu=nu, gamma="scale")
                preds_raw = clf.fit_predict(X_combined)
                preds = [1 if p == -1 else 0 for p in preds_raw]

                p = precision_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
                r = recall_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
                f1 = f1_score(eval_df["true_label"], preds, pos_label=1, zero_division=0)
                acc = accuracy_score(eval_df["true_label"], preds)

                results.append({
                    "Model": f"OC-SVM ({kernel})",
                    "Vectorizer": v_cfg["name"],
                    "Param": f"nu={nu}",
                    "Precision": round(p, 4),
                    "Recall": round(r, 4),
                    "F1-Score": round(f1, 4),
                    "Accuracy": round(acc, 4)
                })

                if f1 > best_f1:
                    best_f1 = f1
                    best_artifacts = {
                        "vectorizer": vectorizer,
                        "scaler": scaler,
                        "model": clf
                    }

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by=["F1-Score", "Precision"], ascending=[False, False]).reset_index(drop=True)
    return results_df, best_artifacts

def main():
    template_miner, eval_df = parse_logs()
    leaderboard, best_artifacts = run_grid_search(eval_df)

    print("================ LEADERBOARD (TOP 10 CONFIGURATIONS) ================")
    print(leaderboard.head(10).to_string(index=False))
    print("=====================================================================")

    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(template_miner, f"{output_dir}/drain3_template_miner.joblib")
    joblib.dump(best_artifacts["vectorizer"], f"{output_dir}/tfidf_vectorizer.joblib")
    joblib.dump(best_artifacts["scaler"], f"{output_dir}/metadata_scaler.joblib")
    joblib.dump(best_artifacts["model"], f"{output_dir}/best_anomaly_detector.joblib")

    best_row = leaderboard.iloc[0]
    print(f"\n🏆 Best Candidate: {best_row['Model']} with {best_row['Vectorizer']} ({best_row['Param']})")
    print(f"   F1-Score: {best_row['F1-Score']} | Precision: {best_row['Precision']} | Recall: {best_row['Recall']}")
    print(f"✅ Best pipeline artifacts saved to '{output_dir}/'")

if __name__ == "__main__":
    main()
"""