# Section 3: Operations Dashboard & Analytics APIs

## 3.1 Overview System Metrics
* **Endpoint:** `GET /api/v1/analytics/summary`[cite: 1]
* **Description:** Provides key performance indicators (ingestion throughput rate, health percentage score, active anomalies count, open critical issues) for top summary cards on the React dashboard home screen[cite: 1].
* **Request:**
  * **Query Parameters:** None[cite: 1]

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    {
      "ingestion_rate_per_sec": 1240,
      "system_health_percentage": 98.4,
      "total_anomalies_today": 12,
      "open_critical_incidents": 2
    }
    ```

---

## 3.2 Log Volume & Anomaly Spikes Chart Data
* **Endpoint:** `GET /api/v1/analytics/volume-chart`[cite: 1]
* **Description:** Supplies aggregated time-series data comparing standard log volume against anomaly frequency spikes to power interactive charts (Recharts / Chart.js)[cite: 1].
* **Request:**
  * **Query Parameters:**
    * `timeframe` (string, optional, default: `"1h"`): Time window filter (`1h`, `24h`, `7d`)[cite: 1].

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    [
      {
        "timestamp": "10:00",
        "normal_logs": 4500,
        "anomalies": 0
      },
      {
        "timestamp": "10:30",
        "normal_logs": 5200,
        "anomalies": 15
      }
    ]
    ```
