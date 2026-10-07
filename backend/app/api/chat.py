"""
Chat/RAG API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ai_question import AIQuestion
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.core.security import get_current_active_user
from app.core.audit import log_activity
from app.services.llm_service import LLMService
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
rag_service = None
llm_service = None
class ChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5


class SourceInfo(BaseModel):
    document_id: int
    chunk_index: int
    page_number: Optional[int] = None
    relevance_score: float
    excerpt: str
    title: Optional[str] = None
    author: Optional[str] = None
    publication_year: Optional[int] = None
    document_type: Optional[str] = None
    category: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    sources: Optional[List[SourceInfo]] = None
    error: Optional[str] = None


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    """
    Ask a question and get an answer with sources
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        global rag_service
        if rag_service is None:
            try:
                from app.services.rag_service import RAGService
                rag_service = RAGService()
            except Exception as initialization_error:
                logger.warning("Semantic RAG unavailable, using database chunk retrieval: %s", initialization_error)
                rag_service = False
        if rag_service:
            result = rag_service.answer_question(question=request.question, top_k=request.top_k, include_sources=True)
        else:
            result = answer_from_database_chunks(request.question, request.top_k or 5, db)
        
        if result['success']:
            document_ids = {source.get('document_id') for source in result.get('sources', [])}
            documents = {
                document.id: document
                for document in db.query(Document).filter(Document.id.in_(document_ids), Document.is_active.is_(True)).all()
            } if document_ids else {}
            for source in result.get('sources', []):
                document = documents.get(source.get('document_id'))
                if document:
                    chunk = db.query(DocumentChunk).filter(
                        DocumentChunk.document_id == document.id,
                        DocumentChunk.chunk_index == source.get('chunk_index'),
                    ).first()
                    source.update({
                        "title": document.title or document.file_name,
                        "author": document.author,
                        "publication_year": document.publication_year,
                        "document_type": document.document_type.name if document.document_type else None,
                        "category": document.category.name if document.category else None,
                        "page_number": chunk.page_number if chunk else source.get('page_number'),
                    })
            db.add(AIQuestion(question=request.question, user_id=current_user.id))
            db.commit()
            log_activity(db, current_user, "Asked AI Question", resource="chat", details=request.question[:500])
            return ChatResponse(
                success=True,
                question=result.get('question'),
                answer=result.get('answer'),
                sources=result.get('sources', [])
            )
        else:
            return ChatResponse(
                success=False,
                error=result.get('error', 'Unknown error')
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


def answer_from_database_chunks(question: str, top_k: int, db: Session) -> Dict:
    """Retrieve real stored chunks as a lightweight fallback when embeddings are unavailable."""
    global llm_service
    terms = [term.lower() for term in question.split() if len(term) > 2]
    chunks = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.is_active.is_(True))
        .order_by(DocumentChunk.created_at.desc())
        .limit(500)
        .all()
    )
    if not chunks:
        processor = DocumentProcessor()
        for document in db.query(Document).filter(Document.is_active.is_(True), Document.is_processed.is_(True)).all():
            if not document.file_path:
                continue
            try:
                processed = processor.process_document(document.file_path, document.file_name, document.id)
                for chunk in processed.get('chunks', []):
                    chunks.append(DocumentChunk(document_id=document.id, chunk_index=chunk['index'], chunk_text=chunk['text'], chunk_length=chunk.get('length', 0), page_number=chunk.get('page_number')))
                if chunks:
                    db.add_all(chunks)
                    db.commit()
            except Exception as processing_error:
                logger.warning("Could not backfill document %s for chat: %s", document.id, processing_error)
    ranked = sorted(chunks, key=lambda chunk: sum(term in chunk.chunk_text.lower() for term in terms), reverse=True)
    selected = [chunk for chunk in ranked if any(term in chunk.chunk_text.lower() for term in terms)][:top_k]
    if not selected:
        return {"success": False, "error": "No relevant stored research content was found."}
    context = "\n\n".join(f"Source document {chunk.document_id}, chunk {chunk.chunk_index}: {chunk.chunk_text}" for chunk in selected)
    if llm_service is None:
        llm_service = LLMService()
    response = llm_service.generate_response(prompt=question, context=context)
    if not response.get('success'):
        return {"success": False, "error": response.get('error', 'The AI service could not generate an answer.')}
    return {
        "success": True,
        "question": question,
        "answer": response.get('answer'),
        "sources": [{"document_id": chunk.document_id, "chunk_index": chunk.chunk_index, "page_number": chunk.page_number, "relevance_score": 1.0, "excerpt": chunk.chunk_text[:500]} for chunk in selected],
    }