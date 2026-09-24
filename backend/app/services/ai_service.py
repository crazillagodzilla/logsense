from datetime import UTC, datetime

from app.models.schemas import IncidentSeverity, LogEntry
from app.services.anomaly_service import (
    AnomalyEvaluation,
    evaluate_log,
    extract_block_id,
)


def parse_log_template(raw_message: str) -> tuple[int | None, str]:
    evaluation = evaluate_log(raw_message)
    return evaluation.parsed.template_id, evaluation.parsed.parsed_template


def evaluate_anomaly(
    raw_message: str,
    previous_template_ids: list[int] | None = None,
) -> AnomalyEvaluation:
    return evaluate_log(raw_message, previous_template_ids)


def should_create_incident(
    log: LogEntry,
    evaluation: AnomalyEvaluation | None = None,
) -> bool:
    if evaluation:
        return evaluation.prediction.is_anomaly
    return evaluate_log(log.raw_message).prediction.is_anomaly


def classify_severity(log: LogEntry) -> IncidentSeverity:
    message = log.raw_message.lower()
    if "fatal" in message or "connection" in message:
        return IncidentSeverity.CRITICAL
    if "error" in message:
        return IncidentSeverity.HIGH
    return IncidentSeverity.MEDIUM


def build_incident_title(log: LogEntry) -> str:
    message = log.raw_message.lower()
    if "connection" in message or "slot" in message:
        return "PostgreSQL Connection Pool Exhaustion"
    return f"{log.log_level} anomaly from {log.source_host}"


def build_rca_markdown(
    log: LogEntry,
    evaluation: AnomalyEvaluation | None = None,
) -> str:
    generated_at = datetime.now(UTC).isoformat()
    model_context = ""
    if evaluation:
        model_context = (
            "\n\n### Model Signal\n"
            f"- Isolation Forest decision score: `{evaluation.prediction.score:.6f}`\n"
            f"- Template sequence length: `{evaluation.prediction.seq_len}`\n"
            f"- Unique templates in sequence: `{evaluation.prediction.unique_templates}`\n"
            f"- Template sequence: `{evaluation.prediction.sequence}`\n"
        )
    return (
        "### Root Cause Analysis\n\n"
        f"LogSense anomaly detection flagged a {log.log_level} log from `{log.source_host}` "
        f"at `{log.timestamp.isoformat()}`. The triggering message was:\n\n"
        f"`{log.raw_message}`\n\n"
        f"Parsed template: `{log.parsed_template}`"
        f"{model_context}\n\n"
        "### Recommended Actions\n"
        "1. Inspect the emitting service and recent deploy activity.\n"
        "2. Check resource pressure and dependency health for the affected host.\n"
        "3. Attach the relevant runbook once FAISS-backed RAG retrieval is enabled.\n\n"
        f"_Generated placeholder RCA at {generated_at}._"
    )
