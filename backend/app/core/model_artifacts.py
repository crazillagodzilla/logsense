from __future__ import annotations

from pathlib import Path

REQUIRED_MODEL_ARTIFACTS = (
    "drain3_template_miner.joblib",
    "tfidf_vectorizer.joblib",
    "metadata_scaler.joblib",
    "best_anomaly_detector.joblib",
)


def ensure_model_artifacts(model_dir: Path | str) -> list[Path]:
    model_path = Path(model_dir)
    missing = [
        model_path / artifact_name
        for artifact_name in REQUIRED_MODEL_ARTIFACTS
        if not (model_path / artifact_name).exists()
    ]

    if missing:
        missing_names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(
            "Model artifacts are missing from "
            f"{model_path}. Missing: {missing_names}. "
            "Run python scripts/download_model_artifacts.py to fetch the required release bundle."
        )

    return [model_path / artifact_name for artifact_name in REQUIRED_MODEL_ARTIFACTS]
