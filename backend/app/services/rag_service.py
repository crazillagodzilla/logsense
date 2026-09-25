import json
import os
import re
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select

from app.core.database import Runbook, engine
from app.models.schemas import RunbookRecord

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
RUNBOOK_ID_PATH = DATA_DIR / "runbook_ids.json"

_MODEL: SentenceTransformer | None = None


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_embedding_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL


def _runbook_search_text(runbook: RunbookRecord | Runbook) -> str:
    title = getattr(runbook, "title", "")
    category = getattr(runbook, "category", "")
    content = getattr(runbook, "content", "")
    return f"Title: {title}\nCategory: {category}\n{content}"


def load_runbook_ids() -> list[int]:
    if not RUNBOOK_ID_PATH.exists():
        return []
    try:
        raw = json.loads(RUNBOOK_ID_PATH.read_text())
        return [int(runbook_id) for runbook_id in raw]
    except (TypeError, ValueError, OSError):
        return []


def _persist_runbook_ids(runbook_ids: list[int]) -> None:
    _ensure_data_dir()
    RUNBOOK_ID_PATH.write_text(json.dumps(runbook_ids, indent=2))


def _load_or_create_index(dimension: int) -> faiss.Index:
    _ensure_data_dir()
    if FAISS_INDEX_PATH.exists():
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        if index.d == dimension:
            return index
        index = faiss.IndexFlatL2(dimension)
        return index
    return faiss.IndexFlatL2(dimension)


def _embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 384), dtype="float32")
    model = _load_embedding_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype="float32")


def index_runbook(runbook: RunbookRecord) -> None:
    _ensure_data_dir()
    embedding = _embed_texts([_runbook_search_text(runbook)])
    index = _load_or_create_index(embedding.shape[1])
    index.add(embedding.astype("float32"))

    runbook_ids = load_runbook_ids()
    if int(runbook.id) not in runbook_ids:
        runbook_ids.append(int(runbook.id))
    _persist_runbook_ids(runbook_ids)
    faiss.write_index(index, str(FAISS_INDEX_PATH))


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) > 2
    }


def _lexical_relevance_score(query: str, runbook: RunbookRecord) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    runbook_text = " ".join(
        filter(
            None,
            [getattr(runbook, "title", ""), getattr(runbook, "category", ""), getattr(runbook, "content", "")],
        )
    )
    runbook_tokens = _tokenize(runbook_text)
    if not runbook_tokens:
        return 0.0

    overlap = query_tokens & runbook_tokens
    if not overlap:
        return 0.0

    return len(overlap) / max(len(query_tokens), 1)


def _load_runbook_record(runbook_id: int) -> RunbookRecord | None:
    with Session(engine) as session:
        runbook = session.get(Runbook, runbook_id)
        if runbook is None:
            return None
        return RunbookRecord(
            id=runbook.id,
            title=runbook.title,
            category=runbook.category,
            content=runbook.content,
            created_at=runbook.created_at,
        )


def search_runbooks(template_sequence: str, raw_message: str, top_k: int = 3) -> list[RunbookRecord]:
    if not FAISS_INDEX_PATH.exists():
        return []
    try:
        index = faiss.read_index(str(FAISS_INDEX_PATH))
    except RuntimeError:
        return []

    if index.ntotal == 0:
        return []

    query_text = (
        f"Template sequence: {template_sequence}\n"
        f"Problem message: {raw_message}"
    )
    query_vector = _embed_texts([query_text]).astype("float32")
    distances, indices = index.search(query_vector, min(top_k * 5, index.ntotal))

    runbook_ids = load_runbook_ids()
    scored_results: list[tuple[float, RunbookRecord]] = []
    for distance, row_index in zip(distances[0], indices[0]):
        if row_index < 0 or row_index >= len(runbook_ids):
            continue

        runbook_id = int(runbook_ids[int(row_index)])
        runbook = _load_runbook_record(runbook_id)
        if runbook is None:
            continue

        lexical_score = _lexical_relevance_score(query_text, runbook)
        semantic_score = 1.0 / (1.0 + float(distance)) if np.isfinite(distance) else 0.0
        combined_score = lexical_score * 5.0 + semantic_score
        scored_results.append((combined_score, runbook))

    if not scored_results:
        return []

    ranked = sorted(scored_results, key=lambda item: item[0], reverse=True)
    return [runbook for _, runbook in ranked[:top_k]]


def _fallback_rag_markdown(
    template_sequence: str,
    raw_message: str,
    runbooks: list[RunbookRecord],
) -> str:
    lines = [
        "### Root Cause Analysis",
        "",
        f"The triggering log pattern `{template_sequence or 'unknown template sequence'}` aligns with a likely operational issue in the application stack.",
        "",
        f"Triggering log: `{raw_message}`",
        "",
    ]
    if runbooks:
        lines.append("### Relevant runbook guidance")
        for i, runbook in enumerate(runbooks, 1):
            lines.append(f"{i}. **{runbook.title}** ({runbook.category})")
            snippet = " ".join(runbook.content.split())
            lines.append(f"   - {snippet[:220]}{'...' if len(snippet) > 220 else ''}")
        lines.append("")
    lines.extend(
        [
            "### Recommended Actions",
            "1. Validate the failing service and recent deploy activity.",
            "2. Inspect resource saturation and dependency health for the affected host.",
            "3. Apply the matching runbook steps and confirm the fix with targeted checks.",
        ]
    )
    return "\n".join(lines)


def generate_gemini_rca(
    template_sequence: str,
    raw_message: str,
    runbooks: list[RunbookRecord],
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_rag_markdown(template_sequence, raw_message, runbooks)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        context = "\n\n".join(
            (
                f"Runbook {index}: {runbook.title} ({runbook.category})\n"
                f"{runbook.content[:800]}"
            )
            for index, runbook in enumerate(runbooks, 1)
        ) or "No runbook matches were found."

        prompt = (
            "You are LogSense's incident RCA assistant. Analyze the triggering log and use the relevant runbooks to produce a concise Markdown incident report.\n\n"
            f"Template sequence: {template_sequence or 'unknown'}\n"
            f"Triggering log: {raw_message}\n\n"
            f"Relevant runbooks:\n{context}\n\n"
            "Return only a polished Markdown document with sections '### Root Cause Analysis', '### Recommended Actions', and a brief summary."
        )

        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if text:
            return text.strip()
        candidates = getattr(response, "candidates", None)
        if candidates:
            parts = candidates[0].content.parts
            text = "".join(getattr(part, "text", "") for part in parts)
            if text:
                return text.strip()
        raise ValueError("Empty Gemini response")
    except Exception:
        return _fallback_rag_markdown(template_sequence, raw_message, runbooks)


def generate_incident_rca(
    template_sequence: str,
    raw_message: str,
    top_k: int = 3,
) -> str:
    runbooks = search_runbooks(template_sequence, raw_message, top_k=top_k)
    return generate_gemini_rca(template_sequence, raw_message, runbooks)
