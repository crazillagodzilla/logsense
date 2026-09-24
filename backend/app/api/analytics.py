from fastapi import APIRouter
from fastapi import Depends
from sqlmodel import Session, func, select

from app.core.database import Incident, Log, get_session
from app.models.schemas import AnalyticsSummary, ChartTimeframe, VolumeChartPoint
from app.services.store import store

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(session: Session = Depends(get_session)) -> AnalyticsSummary:
    open_critical = session.exec(
        select(func.count()).select_from(Incident).where(
            Incident.status == "OPEN",
            Incident.severity == "CRITICAL",
        )
    ).one()
    total_anomalies = session.exec(select(func.count()).select_from(Incident)).one()
    total_logs = session.exec(select(func.count()).select_from(Log)).one()
    health = max(0.0, 100.0 - (open_critical * 0.8) - (total_anomalies * 0.2))

    return AnalyticsSummary(
        ingestion_rate_per_sec=total_logs,
        system_health_percentage=round(health, 1),
        total_anomalies_today=total_anomalies,
        open_critical_incidents=open_critical,
    )


@router.get("/volume-chart", response_model=list[VolumeChartPoint])
def volume_chart(
    timeframe: ChartTimeframe = ChartTimeframe.ONE_HOUR,
) -> list[VolumeChartPoint]:
    return [
        VolumeChartPoint.model_validate(point)
        for point in store.volume_chart(timeframe)
    ]
