# Section 1: Log Ingestion & Live Log Explorer APIs

## 1.1 Live Log Feed Stream
* **Endpoint:** `GET /api/v1/logs/stream`[cite: 1]
* **Description:** Fetches a paginated, filterable list of raw and parsed log entries for the real-time Live Log Explorer[cite: 1].
* **Request:**
  * **Query Parameters:**
    * `limit` (integer, optional, default: `50`): Number of log records to return[cite: 1].
    * `offset` (integer, optional, default: `0`): Pagination offset[cite: 1].
    * `level` (string, optional): Severity level filter (`ERROR`, `WARN`, `INFO`)[cite: 1].
    * `source` (string, optional): Filter by source host (e.g., `db-server-01`)[cite: 1].
    * `search` (string, optional): Keyword query to match in log messages or templates[cite: 1].

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    [
      {
        "id": 1024,
        "timestamp": "2026-09-18T10:30:00Z",
        "source_host": "db-server-01",
        "log_level": "ERROR",
        "raw_message": "psycopg2.OperationalError: FATAL: remaining connection slots are reserved",
        "template_id": 42,
        "parsed_template": "psycopg2.OperationalError: FATAL: remaining connection slots are reserved"
      }
    ]
    ```

---

## 1.2 Log Ingestion Endpoint
* **Endpoint:** `POST /api/v1/logs/ingest`[cite: 1]
* **Description:** Accepts raw log payloads, stores them in PostgreSQL, and queues non-blocking AI anomaly analysis[cite: 1].
* **Request:**
  * **Headers:** `Content-Type: application/json`[cite: 1]
  * **Body Schema:**
    ```json
    {
      "source_host": "db-server-01",
      "log_level": "ERROR",
      "raw_message": "psycopg2.OperationalError: FATAL: remaining connection slots are reserved"
    }
    ```

* **Responses:**
  * **202 Accepted**[cite: 1]
    ```json
    {
      "status": "success",
      "message": "Log ingested and queued for AI evaluation"
    }
    ```

