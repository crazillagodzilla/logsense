from app.models.schemas import RunbookRecord


def index_runbook(runbook: RunbookRecord) -> None:
    """Placeholder for FAISS indexing.

    The API contract is useful before the vector store is fully wired, so this
    function intentionally keeps the side effect boundary in one place.
    """
    return None
