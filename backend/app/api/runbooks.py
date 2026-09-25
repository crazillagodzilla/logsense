from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.core.database import Runbook, get_session
from app.models.schemas import (
    RunbookCreateRequest,
    RunbookCreateResponse,
    RunbookRecord,
    RunbookSummary,
)
from app.services import rag_service

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


def to_runbook_record(runbook: Runbook) -> RunbookRecord:
    return RunbookRecord(
        id=runbook.id,
        title=runbook.title,
        category=runbook.category,
        content=runbook.content,
        created_at=runbook.created_at,
    )


@router.get("", response_model=list[RunbookSummary])
def list_runbooks(
    category: str | None = None,
    session: Session = Depends(get_session),
) -> list[RunbookRecord]:
    statement = select(Runbook).order_by(Runbook.created_at.desc())
    if category:
        statement = statement.where(Runbook.category == category)
    return [to_runbook_record(runbook) for runbook in session.exec(statement).all()]


@router.post(
    "",
    response_model=RunbookCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_runbook(
    payload: RunbookCreateRequest,
    session: Session = Depends(get_session),
) -> RunbookCreateResponse:
    runbook = Runbook(
        title=payload.title,
        category=payload.category,
        content=payload.content,
    )
    session.add(runbook)
    session.commit()
    session.refresh(runbook)
    rag_service.index_runbook(to_runbook_record(runbook))
    return RunbookCreateResponse(
        id=runbook.id,
        message="Runbook saved and indexed into FAISS",
    )
