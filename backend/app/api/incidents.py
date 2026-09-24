from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.database import Incident, Log, get_session
from app.models.schemas import (
    IncidentDetail,
    IncidentSeverity,
    IncidentStatus,
    IncidentStatusUpdateRequest,
    IncidentStatusUpdateResponse,
    IncidentSummary,
    TriggerLog,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def to_incident_summary(incident: Incident) -> IncidentSummary:
    return IncidentSummary(
        id=incident.id,
        created_at=incident.created_at,
        severity=incident.severity,
        title=incident.title,
        status=incident.status,
        trigger_log_id=incident.trigger_log_id,
    )


def to_incident_detail(incident: Incident) -> IncidentDetail:
    trigger_log = None
    if incident.trigger_log:
        trigger_log = TriggerLog(
            id=incident.trigger_log.id,
            raw_message=incident.trigger_log.raw_message,
            source_host=incident.trigger_log.source_host,
        )
    return IncidentDetail(
        **to_incident_summary(incident).model_dump(),
        trigger_log=trigger_log,
        gemini_rca=incident.gemini_rca,
    )


@router.get("", response_model=list[IncidentSummary])
def list_incidents(
    status: IncidentStatus | None = None,
    severity: IncidentSeverity | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_session),
) -> list[IncidentSummary]:
    statement = select(Incident).order_by(Incident.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(Incident.status == status)
    if severity:
        statement = statement.where(Incident.severity == severity)
    return [to_incident_summary(incident) for incident in session.exec(statement).all()]


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(
    incident_id: int,
    session: Session = Depends(get_session),
) -> IncidentDetail:
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.trigger_log_id and not incident.trigger_log:
        incident.trigger_log = session.get(Log, incident.trigger_log_id)
    return to_incident_detail(incident)


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentStatusUpdateResponse,
)
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdateRequest,
    session: Session = Depends(get_session),
) -> IncidentStatusUpdateResponse:
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = payload.status
    incident.updated_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return IncidentStatusUpdateResponse(
        id=incident.id,
        status=incident.status,
        updated_at=incident.updated_at,
    )
