"""
Summarization API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db.database import get_db
from app.services.summarization_service import SummarizationService
from app.core.security import get_current_active_user
from app.models.user import User
from app.core.audit import log_activity

router = APIRouter(prefix="/api/summarize", tags=["summarization"])

# Initialize summarization service
summarization_service = SummarizationService()


class SummarizeRequest(BaseModel):
    document_id: int
    max_tokens: Optional[int] = 500
    temperature: Optional[float] = 0.3


class SummarizeResponse(BaseModel):
    success: bool
    document_id: Optional[int] = None
    document_title: Optional[str] = None
    summary: Optional[Dict[str, str]] = None
    raw_summary: Optional[str] = None
    error: Optional[str] = None


@router.post("/", response_model=SummarizeResponse)
async def summarize_document(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SummarizeResponse:
    """
    Generate a summary for a document
    """
    try:
        result = summarization_service.summarize_document(
            document_id=request.document_id,
            db=db,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        if result.get('success', False):
            log_activity(db, current_user, "Generated Summary", resource=result.get('document_title') or str(request.document_id), details=f"Generated summary for document {request.document_id}")
            return SummarizeResponse(
                success=True,
                document_id=result.get('document_id'),
                document_title=result.get('document_title'),
                summary=result.get('summary'),
                raw_summary=result.get('raw_summary')
            )
        else:
            return SummarizeResponse(
                success=False,
                error=result.get('error', 'Unknown error')
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@router.get("/document/{document_id}")
async def get_summary_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Check if a document can be summarized
    """
    from app.models.document import Document
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": document.id,
        "title": document.title or document.file_name,
        "is_processed": document.is_processed,
        "chunk_count": document.chunk_count,
        "can_summarize": document.is_processed and document.chunk_count > 0
    }