from app.api import analytics
from app.models.schemas import ChartTimeframe, RunbookRecord
from app.services import rag_service


class FakeBucketResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def one(self):
        if not self._rows:
            return 0
        row = self._rows[0]
        if isinstance(row, (list, tuple)):
            return row[0]
        return row


class FakeAnalyticsSession:
    def __init__(self, log_rows=None, incident_rows=None, summary_values=None):
        self.log_rows = log_rows or []
        self.incident_rows = incident_rows or []
        self.summary_values = summary_values or {}

    def exec(self, statement):
        sql = str(statement).lower()
        if "log_count" in sql:
            return FakeBucketResult(self.log_rows)
        if "incident_count" in sql:
            return FakeBucketResult(self.incident_rows)
        if "status" in sql and "severity" in sql and "incidents" in sql:
            return FakeBucketResult([(self.summary_values.get("open_critical", 0),)])
        if "from incidents" in sql and "created_at" in sql:
            return FakeBucketResult([(self.summary_values.get("total_anomalies_today", 0),)])
        if "from logs" in sql:
            return FakeBucketResult([(self.summary_values.get("total_logs", 0),)])
        return FakeBucketResult(self.incident_rows)


def test_index_runbook_persists_faiss_index(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "FAISS_INDEX_PATH", tmp_path / "faiss_index.bin")
    monkeypatch.setattr(rag_service, "RUNBOOK_ID_PATH", tmp_path / "runbook_ids.json")

    runbook = RunbookRecord(
        id=42,
        title="Database pool exhaustion",
        category="postgresql",
        content="Increase max_connections and restart the pool after checking active sessions.",
        created_at="2026-09-24T00:00:00",
    )

    rag_service.index_runbook(runbook)

    assert rag_service.FAISS_INDEX_PATH.exists()
    assert rag_service.load_runbook_ids() == [42]


def test_generate_incident_rca_uses_runbook_context(monkeypatch):
    runbook = RunbookRecord(
        id=5,
        title="Connection pool issue",
        category="postgresql",
        content="Restart the app worker and inspect database connections.",
        created_at="2026-09-24T00:00:00",
    )

    monkeypatch.setattr(rag_service, "search_runbooks", lambda *args, **kwargs: [runbook])
    monkeypatch.setattr(
        rag_service,
        "generate_gemini_rca",
        lambda *args, **kwargs: "### Root Cause Analysis\nDetected database connection exhaustion.",
    )

    result = rag_service.generate_incident_rca(
        template_sequence="512,512,512",
        raw_message="database connection pool exhausted",
        top_k=3,
    )

    assert "### Root Cause Analysis" in result


def test_search_runbooks_prefers_relevant_match_for_database_pool_query(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "FAISS_INDEX_PATH", tmp_path / "faiss_index.bin")
    monkeypatch.setattr(rag_service, "RUNBOOK_ID_PATH", tmp_path / "runbook_ids.json")

    database_runbook = RunbookRecord(
        id=10,
        title="Database connection pool issue",
        category="postgresql",
        content="Increase the max_connections limit, inspect active sessions, and restart the pool after verifying DB resource saturation.",
        created_at="2026-09-24T00:00:00",
    )
    network_runbook = RunbookRecord(
        id=11,
        title="Network packet loss",
        category="network",
        content="Check network interfaces, packet loss trends, and upstream provider health before restarting services.",
        created_at="2026-09-24T00:00:00",
    )

    runbook_by_id = {database_runbook.id: database_runbook, network_runbook.id: network_runbook}
    monkeypatch.setattr(rag_service, "_load_runbook_record", lambda runbook_id: runbook_by_id.get(runbook_id))

    for runbook in (database_runbook, network_runbook):
        rag_service.index_runbook(runbook)

    results = rag_service.search_runbooks(
        template_sequence="database connection pool exhausted",
        raw_message="database connection pool exhausted",
        top_k=2,
    )

    assert results
    assert results[0].title == "Database connection pool issue"


def test_volume_chart_builds_time_bucketed_aggregation():
    session = FakeAnalyticsSession(
        log_rows=[("2026-09-24 10:00:00+00", 120), ("2026-09-24 11:00:00+00", 80)],
        incident_rows=[("2026-09-24 10:00:00+00", 12), ("2026-09-24 11:00:00+00", 8)],
    )

    points = analytics.build_volume_chart(session, ChartTimeframe.TWENTY_FOUR_HOURS)

    assert len(points) == 2
    assert points[0].normal_logs == 108
    assert points[0].anomalies == 12
    assert points[1].normal_logs == 72
    assert points[1].anomalies == 8


def test_analytics_summary_aggregates_live_database_counts():
    session = FakeAnalyticsSession(
        summary_values={
            "total_logs": 7200,
            "total_anomalies_today": 18,
            "open_critical": 2,
        }
    )

    summary = analytics.build_analytics_summary(session)

    assert summary.ingestion_rate_per_sec == 2
    assert summary.total_anomalies_today == 18
    assert summary.open_critical_incidents == 2
    assert summary.system_health_percentage == 94.8


def test_ingest_log_offloads_processing_to_background_tasks(monkeypatch):
    calls = {}

    class RecordingBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            calls["func"] = func
            calls["args"] = args
            calls["kwargs"] = kwargs

    class FakeSession:
        def __init__(self):
            self.saved = []

        def add(self, obj):
            self.saved.append(obj)

        def commit(self):
            return None

        def refresh(self, obj):
            obj.id = 99

    fake_session = FakeSession()
    monkeypatch.setattr("app.api.ingest.get_session", lambda: iter([fake_session]))

    background = RecordingBackgroundTasks()
    payload = {
        "source_host": "app-01",
        "log_level": "ERROR",
        "raw_message": "database connection pool exhausted",
    }

    response = analytics.build_analytics_summary if False else None
    from app.api.ingest import ingest_log
    from app.models.schemas import LogIngestRequest

    result = ingest_log(
        payload=LogIngestRequest(**payload),
        background_tasks=background,
        session=fake_session,
    )

    assert result.status == "success"
    assert calls["func"].__name__ == "process_log_ingestion"
    assert calls["args"][0] == 99
