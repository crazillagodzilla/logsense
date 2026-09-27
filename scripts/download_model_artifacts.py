#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

MODEL_BUNDLE_URL = os.getenv(
    "LOGSENSE_MODEL_BUNDLE_URL",
    "https://github.com/crazillagodzilla/logsense/releases/download/v1.0.0-models/logsense-models-v1.0.0.zip",
)

MODEL_DIR = Path(__file__).resolve().parents[1] / "backend" / "ai_pipeline" / "models"
ARTIFACTS = (
    "drain3_template_miner.joblib",
    "tfidf_vectorizer.joblib",
    "metadata_scaler.joblib",
    "best_anomaly_detector.joblib",
)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_bundle(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading model bundle from {url}")
    with urlopen(url) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    print(f"Saved bundle to {destination}")


def extract_bundle(bundle_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)

    if bundle_path.suffix.lower() == ".zip":
        import zipfile

        with zipfile.ZipFile(bundle_path) as archive:
            archive.extractall(target_dir)
    else:
        with tarfile.open(bundle_path, "r:gz") as archive:
            archive.extractall(target_dir)

    missing = [name for name in ARTIFACTS if not (target_dir / name).exists()]
    if missing:
        missing_list = ", ".join(missing)
        raise FileNotFoundError(f"Downloaded bundle is missing required artifacts: {missing_list}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the LogSense model release bundle.")
    parser.add_argument("--url", default=MODEL_BUNDLE_URL, help="Direct URL to a model bundle archive.")
    parser.add_argument("--output", default=str(MODEL_DIR.parent / "logsense-models.tar.gz"), help="Output archive path.")
    args = parser.parse_args()

    output_path = Path(args.output)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_bundle = Path(tmp_dir) / output_path.name
        download_bundle(args.url, tmp_bundle)
        extract_bundle(tmp_bundle, MODEL_DIR)

    print("Model artifacts downloaded successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
