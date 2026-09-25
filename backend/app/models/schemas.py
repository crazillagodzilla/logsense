from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class LogLevel(StrEnum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class IncidentSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"


class ChartTimeframe(StrEnum):
    ONE_HOUR = "1h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"


class LogIngestRequest(BaseModel):
    source_host: str = Field(min_length=1, max_length=100)
    log_level: LogLevel
    raw_message: str = Field(min_length=1)


class StatusMessage(BaseModel):
    status: str
    message: str


class LogEntry(BaseModel):
    id: int
    timestamp: datetime
    source_host: str
    log_level: LogLevel
    raw_message: str
    template_id: Optional[int] = None
    parsed_template: Optional[str] = None


class IncidentSummary(BaseModel):
    id: int
    created_at: datetime
    severity: IncidentSeverity
    title: str
    status: IncidentStatus
    trigger_log_id: Optional[int] = None


class TriggerLog(BaseModel):
    id: int
    raw_message: str
    source_host: str


class IncidentDetail(IncidentSummary):
    trigger_log: Optional[TriggerLog] = None
    gemini_rca: str


class IncidentStatusUpdateRequest(BaseModel):
    status: IncidentStatus


class IncidentStatusUpdateResponse(BaseModel):
    id: int
    status: IncidentStatus
    updated_at: datetime


class AnalyticsSummary(BaseModel):
    ingestion_rate_per_sec: int
    system_health_percentage: float
    total_anomalies_today: int
    open_critical_incidents: int


class VolumeChartPoint(BaseModel):
    timestamp: str
    normal_logs: int
    anomalies: int


class RunbookSummary(BaseModel):
    id: int
    title: str
    category: str
    created_at: datetime


class RunbookCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class RunbookCreateResponse(BaseModel):
    id: int
    message: str


class RunbookRecord(RunbookSummary):
    content: str

