# Section 4: Knowledge Base & RAG Runbook Management APIs

## 4.1 List Knowledge Base Runbooks
* **Endpoint:** `GET /api/v1/runbooks`
* **Description:** Retrieves a list of all indexed troubleshooting guides and operational runbooks stored in PostgreSQL[cite: 1].
* **Request:**
  * **Query Parameters:**
    * `category` (string, optional): Filter by operational domain (e.g., `Database`, `Network`, `Application`)[cite: 1].

* **Responses:**
  * **200 OK**[cite: 1]
    ```json
    [
      {
        "id": 12,
        "title": "PostgreSQL Connection Troubleshooting Guide",
        "category": "Database",
        "created_at": "2026-09-15T08:00:00Z"
      }
    ]
    ```

---

## 4.2 Create & Index New Runbook
* **Endpoint:** `POST /api/v1/runbooks`[cite: 1]
* **Description:** Stores a new runbook in PostgreSQL and automatically generates vector embeddings to update the FAISS vector store for future RAG searches[cite: 1].
* **Request:**
  * **Headers:** `Content-Type: application/json`[cite: 1]
  * **Body Schema:**
    ```json
    {
      "title": "PostgreSQL Connection Troubleshooting Guide",
      "category": "Database",
      "content": "# Handling Connection Limits\nWhen PostgreSQL runs out of slots, restart worker process or bump max_connections..."
    }
    ```

* **Responses:**
  * **201 Created**[cite: 1]
    ```json
    {
      "id": 12,
      "message": "Runbook saved and indexed into FAISS"
    }
    ```
