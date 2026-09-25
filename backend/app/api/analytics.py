from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from fastapi import Depends
from sqlmodel import Session, func, select

from app.core.database import Incident, Log, get_session
from app.models.schemas import AnalyticsSummary, ChartTimeframe, VolumeChartPoint

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _time_window_for(timeframe: ChartTimeframe) -> tuple[datetime, str]:
    now = datetime.now(UTC)
    if timeframe == ChartTimeframe.ONE_HOUR:
        return now - timedelta(hours=1), "hour"
    if timeframe == ChartTimeframe.TWENTY_FOUR_HOURS:
        return now - timedelta(hours=24), "hour"
    return now - timedelta(days=7), "day"


def _bucket_for_timeframe(timeframe: ChartTimeframe):
    _, granularity = _time_window_for(timeframe)
    if granularity == "hour":
        return func.date_trunc("hour", Log.timestamp)
    return func.date_trunc("day", Log.timestamp)


def _format_bucket_label(bucket_value: datetime | None) -> str:
    if bucket_value is None:
        return "unknown"
    if hasattr(bucket_value, "strftime"):
        return bucket_value.strftime("%Y-%m-%dT%H:%M:%S")
    return str(bucket_value)


def build_volume_chart(
    session: Session,
    timeframe: ChartTimeframe = ChartTimeframe.ONE_HOUR,
) -> list[VolumeChartPoint]:
    start_time, _ = _time_window_for(timeframe)
    bucket = _bucket_for_timeframe(timeframe)

    log_rows = session.exec(
        select(bucket.label("bucket"), func.count(Log.id).label("log_count"))
        .where(Log.timestamp >= start_time)
        .group_by(bucket)
        .order_by(bucket)
    ).all()

    incident_rows = session.exec(
        select(bucket.label("bucket"), func.count(Incident.id).label("incident_count"))
        .where(Incident.created_at >= start_time)
        .group_by(bucket)
        .order_by(bucket)
    ).all()

    incident_map = {row[0]: int(row[1]) for row in incident_rows}

    chart_points: list[VolumeChartPoint] = []
    for row in log_rows:
        bucket_value = row[0]
        log_count = int(row[1])
        anomaly_count = incident_map.get(bucket_value, 0)
        chart_points.append(
            VolumeChartPoint(
                timestamp=_format_bucket_label(bucket_value),
                normal_logs=max(log_count - anomaly_count, 0),
                anomalies=anomaly_count,
            )
        )

    return chart_points


def build_analytics_summary(session: Session) -> AnalyticsSummary:
    open_critical = session.exec(
        select(func.count()).select_from(Incident).where(
            Incident.status == "OPEN",
            Incident.severity == "CRITICAL",
        )
    ).one()

    today_start = datetime.now(UTC) - timedelta(days=1)
    total_anomalies = session.exec(
        select(func.count()).select_from(Incident).where(
            Incident.created_at >= today_start,
        )
    ).one()
    total_logs = session.exec(
        select(func.count()).select_from(Log).where(
            Log.timestamp >= today_start,
        )
    ).one()
    ingestion_rate_per_sec = max(0, int(round(total_logs / 3600)))
    health = max(0.0, 100.0 - (open_critical * 0.8) - (total_anomalies * 0.2))

    return AnalyticsSummary(
        ingestion_rate_per_sec=ingestion_rate_per_sec,
        system_health_percentage=round(health, 1),
        total_anomalies_today=total_anomalies,
        open_critical_incidents=open_critical,
    )


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(session: Session = Depends(get_session)) -> AnalyticsSummary:
    return build_analytics_summary(session)


@router.get("/volume-chart", response_model=list[VolumeChartPoint])
def volume_chart(
    timeframe: ChartTimeframe = ChartTimeframe.ONE_HOUR,
    session: Session = Depends(get_session),
) -> list[VolumeChartPoint]:
    return build_volume_chart(session, timeframe)
