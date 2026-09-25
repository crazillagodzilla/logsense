# Section 2: Incident Management & AI Root-Cause Analysis (RCA) APIs

## 2.1 Fetch Active & Historical Incidents
* **Endpoint:** `GET /api/v1/incidents`[cite: 1]
* **Description:** Retrieves a list of flagged anomaly incidents for the Incident Center and top alert feeds[cite: 1].
* **Request:**
  * **Query Parameters:**
    * `status` (string, optional): Filter by lifecycle status (`OPEN`, `INVESTIGATING`, `RESOLVED`)[cite: 1].
    * `severity` (string, optional): Filter by severity level (`CRITICAL`, `HIGH`, `MEDIUM`)[cite: 1].
    * `limit` (integer, optional, default: `20`): Maximum items to retrieve[cite: 1].

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    [
      {
        "id": 501,
        "created_at": "2026-09-18T10:30:05Z",
        "severity": "CRITICAL",
        "title": "PostgreSQL Connection Pool Exhaustion",
        "status": "OPEN",
        "trigger_log_id": 1024
      }
    ]
    ```

---

## 2.2 Detailed Incident View & Gemini RCA Report
* **Endpoint:** `GET /api/v1/incidents/{incident_id}`[cite: 1]
* **Description:** Fetches detailed information for a specific incident to render inside the Incident Drawer, including Gemini's Markdown-formatted root-cause explanation, triggering log details, and recommended action steps[cite: 1].
* **Request:**
  * **Path Parameters:**
    * `incident_id` (integer, required): Unique ID of the incident report[cite: 1].

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    {
      "id": 501,
      "created_at": "2026-09-18T10:30:05Z",
      "severity": "CRITICAL",
      "title": "PostgreSQL Connection Pool Exhaustion",
      "status": "OPEN",
      "trigger_log": {
        "id": 1024,
        "raw_message": "psycopg2.OperationalError: FATAL: remaining connection slots are reserved",
        "source_host": "db-server-01"
      },
      "gemini_rca": "### Root Cause Analysis\n\nThe application server exhausted the available PostgreSQL connection pool due to a sudden surge in unclosed database sessions.\n\n### Recommended Actions\n1. Restart the database pool worker: systemctl restart pg_pool\n2. Increase max_connections in postgresql.conf from 100 to 300."
    }
    ```

---

## 2.3 Update Incident Status
* **Endpoint:** `PATCH /api/v1/incidents/{incident_id}/status`[cite: 1]
* **Description:** Updates the operational status of an incident directly from the UI[cite: 1].
* **Request:**
  * **Path Parameters:**
    * `incident_id` (integer, required): Incident unique ID[cite: 1].
  * **Body Schema:**
    ```json
    {
      "status": "RESOLVED"
    }
    ```

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    {
      "id": 501,
      "status": "RESOLVED",
      "updated_at": "2026-09-18T10:35:00Z"
    }
    ```
