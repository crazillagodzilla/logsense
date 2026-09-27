from pathlib import Path

import pytest

from app.core.model_artifacts import ensure_model_artifacts


def test_ensure_model_artifacts_accepts_complete_bundle(tmp_path: Path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    for name in (
        "drain3_template_miner.joblib",
        "tfidf_vectorizer.joblib",
        "metadata_scaler.joblib",
        "best_anomaly_detector.joblib",
    ):
        (model_dir / name).write_text(name)

    found = ensure_model_artifacts(model_dir)

    assert [path.name for path in found] == [
        "drain3_template_miner.joblib",
        "tfidf_vectorizer.joblib",
        "metadata_scaler.joblib",
        "best_anomaly_detector.joblib",
    ]


def test_ensure_model_artifacts_raises_clear_error_for_missing_file(tmp_path: Path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "drain3_template_miner.joblib").write_text("present")

    with pytest.raises(FileNotFoundError, match="Run python scripts/download_model_artifacts.py"):
        ensure_model_artifacts(model_dir)
