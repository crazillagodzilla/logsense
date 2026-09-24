from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, or_, select

from app.core.database import Incident, Log, get_session
from app.models.schemas import LogEntry, LogIngestRequest, LogLevel, StatusMessage
from app.services import ai_service

router = APIRouter(prefix="/logs", tags=["logs"])


def to_log_entry(log: Log) -> LogEntry:
    return LogEntry(
        id=log.id,
        timestamp=log.timestamp,
        source_host=log.source_host,
        log_level=log.log_level,
        raw_message=log.raw_message,
        template_id=log.template_id,
        parsed_template=log.parsed_template,
    )


@router.get("/stream", response_model=list[LogEntry])
def stream_logs(
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    level: LogLevel | None = None,
    source: str | None = None,
    search: str | None = None,
    session: Session = Depends(get_session),
) -> list[LogEntry]:
    statement = select(Log).order_by(Log.timestamp.desc()).offset(offset).limit(limit)
    if level:
        statement = statement.where(Log.log_level == level)
    if source:
        statement = statement.where(Log.source_host == source)
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(Log.raw_message.ilike(pattern), Log.parsed_template.ilike(pattern))
        )
    return [to_log_entry(log) for log in session.exec(statement).all()]


@router.post(
    "/ingest",
    response_model=StatusMessage,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_log(
    payload: LogIngestRequest,
    session: Session = Depends(get_session),
) -> StatusMessage:
    block_id = ai_service.extract_block_id(payload.raw_message)
    previous_template_ids: list[int] = []
    if block_id:
        previous_logs = session.exec(
            select(Log)
            .where(Log.raw_message.ilike(f"%{block_id}%"), Log.template_id.is_not(None))
            .order_by(Log.timestamp.asc())
            .limit(250)
        ).all()
        previous_template_ids = [
            log.template_id for log in previous_logs if log.template_id is not None
        ]

    evaluation = ai_service.evaluate_anomaly(
        payload.raw_message,
        previous_template_ids=previous_template_ids,
    )
    log = Log(
        source_host=payload.source_host,
        log_level=payload.log_level,
        raw_message=payload.raw_message,
        template_id=evaluation.parsed.template_id,
        parsed_template=evaluation.parsed.parsed_template,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    log_entry = to_log_entry(log)
    if ai_service.should_create_incident(log_entry, evaluation):
        session.add(
            Incident(
                severity=ai_service.classify_severity(log_entry),
                title=ai_service.build_incident_title(log_entry),
                status="OPEN",
                trigger_log_id=log.id,
                gemini_rca=ai_service.build_rca_markdown(log_entry, evaluation),
            )
        )
        session.commit()

    return StatusMessage(
        status="success",
        message="Log ingested and queued for AI evaluation",
    )
