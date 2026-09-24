from datetime import UTC, datetime, timedelta
from itertools import count
from threading import Lock

from app.models.schemas import (
    ChartTimeframe,
    IncidentDetail,
    IncidentSeverity,
    IncidentStatus,
    LogEntry,
    LogIngestRequest,
    RunbookCreateRequest,
    RunbookRecord,
    TriggerLog,
)
from app.services import ai_service, rag_service


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._log_ids = count(1025)
        self._incident_ids = count(502)
        self._runbook_ids = count(13)

        now = datetime(2026, 9, 18, 10, 30, tzinfo=UTC)
        self.logs: list[LogEntry] = [
            LogEntry(
                id=1024,
                timestamp=now,
                source_host="db-server-01",
                log_level="ERROR",
                raw_message="psycopg2.OperationalError: FATAL: remaining connection slots are reserved",
                template_id=42,
                parsed_template="psycopg2.OperationalError: FATAL: remaining connection slots are reserved",
            )
        ]
        self.incidents: list[IncidentDetail] = [
            IncidentDetail(
                id=501,
                created_at=now + timedelta(seconds=5),
                severity=IncidentSeverity.CRITICAL,
                title="PostgreSQL Connection Pool Exhaustion",
                status=IncidentStatus.OPEN,
                trigger_log_id=1024,
                trigger_log=TriggerLog(
                    id=1024,
                    raw_message=self.logs[0].raw_message,
                    source_host=self.logs[0].source_host,
                ),
                gemini_rca=(
                    "### Root Cause Analysis\n\n"
                    "The application server exhausted the available PostgreSQL "
                    "connection pool due to a sudden surge in unclosed database sessions.\n\n"
                    "### Recommended Actions\n"
                    "1. Restart the database pool worker: systemctl restart pg_pool\n"
                    "2. Increase max_connections in postgresql.conf from 100 to 300."
                ),
            )
        ]
        self.runbooks: list[RunbookRecord] = [
            RunbookRecord(
                id=12,
                title="PostgreSQL Connection Troubleshooting Guide",
                category="Database",
                content=(
                    "# Handling Connection Limits\n"
                    "When PostgreSQL runs out of slots, restart worker process or "
                    "bump max_connections after validating workload."
                ),
                created_at=datetime(2026, 9, 15, 8, 0, tzinfo=UTC),
            )
        ]

    def list_logs(
        self,
        *,
        limit: int,
        offset: int,
        level: str | None,
        source: str | None,
        search: str | None,
    ) -> list[LogEntry]:
        logs = self.logs
        if level:
            logs = [log for log in logs if log.log_level == level]
        if source:
            logs = [log for log in logs if log.source_host == source]
        if search:
            needle = search.lower()
            logs = [
                log
                for log in logs
                if needle in log.raw_message.lower()
                or needle in (log.parsed_template or "").lower()
            ]
        return logs[offset : offset + limit]

    def ingest_log(self, payload: LogIngestRequest) -> LogEntry:
        template_id, parsed_template = ai_service.parse_log_template(payload.raw_message)
        with self._lock:
            log = LogEntry(
                id=next(self._log_ids),
                timestamp=datetime.now(UTC),
                source_host=payload.source_host,
                log_level=payload.log_level,
                raw_message=payload.raw_message,
                template_id=template_id,
                parsed_template=parsed_template,
            )
            self.logs.insert(0, log)
            if ai_service.should_create_incident(log):
                self.incidents.insert(0, self._create_incident(log))
            return log

    def _create_incident(self, log: LogEntry) -> IncidentDetail:
        return IncidentDetail(
            id=next(self._incident_ids),
            created_at=datetime.now(UTC),
            severity=ai_service.classify_severity(log),
            title=ai_service.build_incident_title(log),
            status=IncidentStatus.OPEN,
            trigger_log_id=log.id,
            trigger_log=TriggerLog(
                id=log.id,
                raw_message=log.raw_message,
                source_host=log.source_host,
            ),
            gemini_rca=ai_service.build_rca_markdown(log),
        )

    def list_incidents(
        self,
        *,
        status: str | None,
        severity: str | None,
        limit: int,
    ) -> list[IncidentDetail]:
        incidents = self.incidents
        if status:
            incidents = [incident for incident in incidents if incident.status == status]
        if severity:
            incidents = [
                incident for incident in incidents if incident.severity == severity
            ]
        return incidents[:limit]

    def get_incident(self, incident_id: int) -> IncidentDetail | None:
        return next(
            (incident for incident in self.incidents if incident.id == incident_id),
            None,
        )

    def update_incident_status(
        self,
        incident_id: int,
        status: IncidentStatus,
    ) -> IncidentDetail | None:
        with self._lock:
            incident = self.get_incident(incident_id)
            if not incident:
                return None
            incident.status = status
            return incident

    def list_runbooks(self, category: str | None) -> list[RunbookRecord]:
        if category:
            return [
                runbook for runbook in self.runbooks if runbook.category == category
            ]
        return self.runbooks

    def create_runbook(self, payload: RunbookCreateRequest) -> RunbookRecord:
        with self._lock:
            runbook = RunbookRecord(
                id=next(self._runbook_ids),
                title=payload.title,
                category=payload.category,
                content=payload.content,
                created_at=datetime.now(UTC),
            )
            self.runbooks.insert(0, runbook)
            rag_service.index_runbook(runbook)
            return runbook

    def volume_chart(self, timeframe: ChartTimeframe) -> list[dict[str, int | str]]:
        if timeframe == ChartTimeframe.ONE_HOUR:
            return [
                {"timestamp": "10:00", "normal_logs": 4500, "anomalies": 0},
                {"timestamp": "10:30", "normal_logs": 5200, "anomalies": 15},
            ]
        if timeframe == ChartTimeframe.TWENTY_FOUR_HOURS:
            return [
                {"timestamp": "00:00", "normal_logs": 32000, "anomalies": 4},
                {"timestamp": "06:00", "normal_logs": 41000, "anomalies": 8},
                {"timestamp": "12:00", "normal_logs": 53500, "anomalies": 18},
                {"timestamp": "18:00", "normal_logs": 47000, "anomalies": 6},
            ]
        return [
            {"timestamp": "Mon", "normal_logs": 238000, "anomalies": 20},
            {"timestamp": "Tue", "normal_logs": 251000, "anomalies": 17},
            {"timestamp": "Wed", "normal_logs": 264000, "anomalies": 25},
            {"timestamp": "Thu", "normal_logs": 248000, "anomalies": 14},
            {"timestamp": "Fri", "normal_logs": 277000, "anomalies": 29},
            {"timestamp": "Sat", "normal_logs": 193000, "anomalies": 7},
            {"timestamp": "Sun", "normal_logs": 184000, "anomalies": 5},
        ]


store = InMemoryStore()
