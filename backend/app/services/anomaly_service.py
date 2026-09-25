from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from threading import Lock
from typing import Iterable
import warnings

import joblib
import pandas as pd
import scipy.sparse as sp
from sklearn.exceptions import InconsistentVersionWarning


MODEL_DIR = Path(__file__).resolve().parents[2] / "ai_pipeline" / "models"
BLOCK_ID_PATTERN = re.compile(r"(blk_-?\d+)")


@dataclass(frozen=True)
class ParsedLogTemplate:
    template_id: int | None
    template_token: str | None
    parsed_template: str
    block_id: str | None


@dataclass(frozen=True)
class AnomalyPrediction:
    is_anomaly: bool
    score: float
    sequence: str
    seq_len: int
    unique_templates: int


@dataclass(frozen=True)
class AnomalyEvaluation:
    parsed: ParsedLogTemplate
    prediction: AnomalyPrediction


class AnomalyDetector:
    def __init__(self, model_dir: Path = MODEL_DIR) -> None:
        self.model_dir = model_dir
        self._lock = Lock()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InconsistentVersionWarning)
            self.template_miner = joblib.load(model_dir / "drain3_template_miner.joblib")
            self.vectorizer = joblib.load(model_dir / "tfidf_vectorizer.joblib")
            self.scaler = joblib.load(model_dir / "metadata_scaler.joblib")
            self.model = joblib.load(model_dir / "best_anomaly_detector.joblib")

    def parse(self, raw_message: str) -> ParsedLogTemplate:
        with self._lock:
            result = self.template_miner.add_log_message(raw_message)

        cluster_id = result.get("cluster_id")
        template_token = f"E{cluster_id}" if cluster_id is not None else None
        return ParsedLogTemplate(
            template_id=cluster_id,
            template_token=template_token,
            parsed_template=result.get("template_mined") or raw_message,
            block_id=self.extract_block_id(raw_message),
        )

    def predict(self, template_tokens: Iterable[str]) -> AnomalyPrediction:
        sequence_tokens = [token for token in template_tokens if token]
        if not sequence_tokens:
            sequence_tokens = ["E0"]

        sequence = " ".join(sequence_tokens)
        metadata = pd.DataFrame(
            [
                {
                    "seq_len": len(sequence_tokens),
                    "unique_templates": len(set(sequence_tokens)),
                }
            ]
        )
        x_tfidf = self.vectorizer.transform([sequence])
        x_meta = self.scaler.transform(metadata)
        features = sp.hstack([x_tfidf, x_meta], format="csr")

        raw_prediction = int(self.model.predict(features)[0])
        score = float(self.model.decision_function(features)[0])
        return AnomalyPrediction(
            is_anomaly=raw_prediction == -1,
            score=score,
            sequence=sequence,
            seq_len=len(sequence_tokens),
            unique_templates=len(set(sequence_tokens)),
        )

    def evaluate(
        self,
        raw_message: str,
        previous_template_ids: Iterable[int] | None = None,
    ) -> AnomalyEvaluation:
        parsed = self.parse(raw_message)
        template_tokens = [f"E{template_id}" for template_id in previous_template_ids or []]
        if parsed.template_token:
            template_tokens.append(parsed.template_token)
        prediction = self.predict(template_tokens)
        return AnomalyEvaluation(parsed=parsed, prediction=prediction)

    @staticmethod
    def extract_block_id(raw_message: str) -> str | None:
        match = BLOCK_ID_PATTERN.search(raw_message)
        return match.group(1) if match else None


@lru_cache(maxsize=1)
def get_anomaly_detector() -> AnomalyDetector:
    return AnomalyDetector()


def evaluate_log(
    raw_message: str,
    previous_template_ids: Iterable[int] | None = None,
) -> AnomalyEvaluation:
    return get_anomaly_detector().evaluate(raw_message, previous_template_ids)


def extract_block_id(raw_message: str) -> str | None:
    return AnomalyDetector.extract_block_id(raw_message)
