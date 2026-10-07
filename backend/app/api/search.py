"""
Search API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import re
from sqlalchemy.orm import Session
import logging

from app.db.database import get_db
from app.models.document import Document, DocumentChunk
from app.core.security import get_current_active_user
from app.models.user import User
from app.core.audit import log_activity

router = APIRouter(prefix="/api/search", tags=["search"])
service = None
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@router.post("/")
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[dict]:
    """
    Search for relevant document chunks
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        global service
        if service is None:
            try:
                from app.services.document_service import DocumentService
                service = DocumentService()
            except Exception as initialization_error:
                logger.warning("Semantic embeddings unavailable, using database search: %s", initialization_error)
                service = False
        top_k = min(max(request.top_k or 5, 1), 50)
        if service:
            results = service.search_documents(query=request.query, top_k=top_k)
            query_terms = [term.lower() for term in re.findall(r"[\w'-]+", request.query) if len(term) > 2]
            for result in results:
                result.setdefault("metadata", {})["query_terms"] = query_terms
            enriched = enrich_results(results, db, top_k)
            if len(enriched) < top_k:
                existing_ids = {result['id'] for result in enriched}
                for result in database_search(request.query, top_k, db):
                    if result['id'] not in existing_ids:
                        enriched.append(result)
                    if len(enriched) >= top_k:
                        break
            log_activity(db, current_user, "Searched Documents", resource="search", details=request.query[:500])
            return enriched
        results = database_search(request.query, top_k, db)
        log_activity(db, current_user, "Searched Documents", resource="search", details=request.query[:500])
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


def enrich_results(results: List[dict], db: Session, top_k: int) -> List[dict]:
    """Attach current document metadata and hide deleted documents from vector results."""
    document_ids = {result.get("metadata", {}).get("document_id") for result in results}
    document_ids.discard(None)
    documents = {
        document.id: document
        for document in db.query(Document).filter(Document.id.in_(document_ids), Document.is_active.is_(True)).all()
    }
    enriched = []
    for result in results:
        metadata = result.setdefault("metadata", {})
        document = documents.get(metadata.get("document_id"))
        if not document:
            continue
        metadata.update({
            "title": document.title,
            "author": document.author,
            "publication_year": document.publication_year,
            "publication_period": document.publication_period,
            "document_type": document.document_type.name if document.document_type else None,
            "category": document.category.name if document.category else None,
            "topics": [topic.name for topic in document.topics],
            "excerpt": make_excerpt(result.get("document", ""), metadata.get("query_terms", [])),
            "document_name": document.file_name,
        })
        if metadata.get("chunk_index") is not None:
            chunk = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document.id,
                DocumentChunk.chunk_index == metadata["chunk_index"],
            ).first()
            metadata["page_number"] = chunk.page_number if chunk else metadata.get("page_number")
        enriched.append(result)
        if len(enriched) >= top_k:
            break
    return enriched


def database_search(query: str, top_k: int, db: Session) -> List[dict]:
    """Search persisted processed research chunks without fabricating result content."""
    terms = [term.lower() for term in re.findall(r"[\w'-]+", query) if len(term) > 2]
    chunks = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.is_active.is_(True))
        .order_by(DocumentChunk.created_at.desc())
        .limit(1000)
        .all()
    )
    ranked = sorted(
        chunks,
        key=lambda chunk: sum(bool(re.search(rf"\b{re.escape(term)}\b", chunk.chunk_text.lower())) for term in terms) + sum(bool(re.search(rf"\b{re.escape(term)}\b", (chunk.document.title + ' ' + chunk.document.file_name).lower())) * 2 for term in terms),
        reverse=True,
    )
    results = []
    for chunk in ranked:
        score = sum(bool(re.search(rf"\b{re.escape(term)}\b", chunk.chunk_text.lower())) for term in terms)
        score += sum(bool(re.search(rf"\b{re.escape(term)}\b", (chunk.document.title + ' ' + chunk.document.file_name).lower())) * 2 for term in terms)
        if score == 0:
            continue
        results.append({
            "id": f"db_{chunk.document_id}_{chunk.chunk_index}",
            "document": chunk.chunk_text,
            "metadata": {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "excerpt": make_excerpt(chunk.chunk_text, terms),
                "title": chunk.document.title,
                "document_name": chunk.document.file_name,
                "author": chunk.document.author,
                "publication_year": chunk.document.publication_year,
                "publication_period": chunk.document.publication_period,
                "page_number": chunk.page_number,
            },
            "distance": round(1 / (score + 1), 4),
        })
        if len(results) >= top_k:
            break
    return results


def make_excerpt(text: str, terms: List[str]) -> str:
    """Return complete-word context around the first matching term."""
    clean_text = " ".join((text or "").split())
    if not clean_text:
        return ""
    match = next((re.search(rf"\b{re.escape(term)}\b", clean_text, re.IGNORECASE) for term in terms), None)
    if not match:
        return clean_text[:500]
    start = max(0, match.start() - 180)
    end = min(len(clean_text), match.end() + 320)
    while start > 0 and not clean_text[start].isspace():
        start -= 1
    while end < len(clean_text) and not clean_text[end - 1].isspace():
        end += 1
    return ("..." if start else "") + clean_text[start:end].strip() + ("..." if end < len(clean_text) else "")