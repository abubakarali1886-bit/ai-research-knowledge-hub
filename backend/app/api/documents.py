"""
Document Upload and Management API Endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import re
import hashlib
import uuid
import logging
import json
import tempfile
from datetime import datetime

from app.db.database import get_db
from app.models.document import Document, DocumentChunk, Category, DocumentType, Keyword, ResearchTopic
from app.models.saved_research import SavedResearch
from app.core.security import get_current_active_user, require_researcher
from app.core.audit import log_activity
from app.models.user import User
from app.services.document_processor import DocumentProcessor

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Initialize document processor
processor = DocumentProcessor()

# Upload directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger = logging.getLogger(__name__)


class DocumentMetadataUpdate(BaseModel):
    title: str
    author: str = ""
    publication_year: int | None = None


@router.post("/upload/preview")
async def preview_upload(
    file: UploadFile = File(...),
    current_user: User = Depends(require_researcher),
):
    """Extract metadata without creating a document, chunks, or embeddings."""
    is_valid, error_msg = processor.validate_file(file.filename, file.size or 0, file.content_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > processor.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum allowed limit of 50 MB.")
    suffix = os.path.splitext(file.filename or "document")[1].lower()
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(contents)
            temporary_path = temporary_file.name
        result = processor.process_document(temporary_path, os.path.basename(file.filename or "document"), 0)
        metadata = result.get("metadata", {})
        return {
            "file_name": file.filename,
            "title": metadata.get("title") or os.path.splitext(file.filename or "document")[0],
            "authors": metadata.get("authors", []),
            "author": metadata.get("author"),
            "author_type": metadata.get("author_type", "unknown"),
            "author_confidence": metadata.get("author_confidence", 0),
            "author_source": metadata.get("author_source"),
            "metadata_review_status": metadata.get("metadata_review_status", "needs_review"),
            "publication_year": metadata.get("publication_year"),
            "publication_year_confidence": metadata.get("publication_year_confidence", 0),
            "publication_year_source": metadata.get("publication_year_source"),
            "publication_period": metadata.get("publication_period"),
            "department": metadata.get("department"),
            "document_type": metadata.get("document_type"),
            "category": metadata.get("category"),
            "topics": metadata.get("topics", []),
            "keywords": metadata.get("keywords", []),
            "total_pages": result.get("total_pages", 0),
        }
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    author: str = Form(None),
    publication_year: str = Form(None),
    department: str = Form(None),
    document_type: str = Form(None),
    topics: str = Form(None),
    authors_json: str = Form(None),
    author_type: str = Form(None),
    author_confidence: float = Form(None),
    author_source: str = Form(None),
    metadata_review_status: str = Form("reviewed"),
    category_id: int = None,
    document_type_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_researcher)
):
    """
    Upload and process a document
    """
    if file.size and file.size > processor.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds the maximum allowed limit of 50 MB.")
    # Validate file
    is_valid, error_msg = processor.validate_file(file.filename, file.size or 0, file.content_type)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > processor.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds {processor.MAX_FILE_SIZE / 1024 / 1024} MB limit")

    file_hash = hashlib.sha256(contents).hexdigest()
    for existing in db.query(Document).filter(Document.is_active.is_(True)).all():
        if existing.file_path and os.path.isfile(existing.file_path):
            with open(existing.file_path, "rb") as existing_file:
                if hashlib.sha256(existing_file.read()).hexdigest() == file_hash:
                    raise HTTPException(status_code=409, detail="This document has already been uploaded.")
    
    # Save file
    original_filename = os.path.basename(file.filename or "document")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    try:
        # Save file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        # Determine file type
        file_extension = os.path.splitext(original_filename)[1].lstrip('.').lower()
        file_size = os.path.getsize(file_path)
        
        # Create document record
        requested_year = None
        requested_period = None
        if publication_year:
            year_match = re.search(r'\b((?:19|20)\d{2})(?:\s*(?:-|–|—|to|/)\s*((?:19|20)\d{2}))?\b', publication_year)
            if year_match:
                requested_year = int(year_match.group(1))
                requested_period = f'{year_match.group(1)}-{year_match.group(2)}' if year_match.group(2) else None

        document = Document(
            title=title or original_filename,
            author=author,
            authors_json=authors_json,
            author_type=author_type or "unknown",
            author_confidence=author_confidence,
            author_source=author_source,
            metadata_review_status=metadata_review_status or "needs_review",
            publication_year=requested_year,
            publication_period=requested_period,
            file_path=file_path,
            file_name=original_filename,
            file_size=file_size,
            file_type=file_extension,
            category_id=category_id,
            document_type_id=document_type_id,
            is_processed=False,
            processing_status="pending",
            uploader_id=current_user.id,
        )
        db.add(document)

        if department and not category_id:
            document.category = db.query(Category).filter(Category.name == department.strip()).first()
            if not document.category:
                document.category = Category(name=department.strip(), description="Uploaded document department")
        if document_type and not document_type_id:
            document.document_type = db.query(DocumentType).filter(DocumentType.name == document_type.strip()).first()
            if not document.document_type:
                document.document_type = DocumentType(name=document_type.strip(), description="Uploaded document type")
        if topics:
            for topic_name in {topic.strip() for topic in topics.split(',') if topic.strip()}:
                topic = db.query(ResearchTopic).filter(ResearchTopic.name.ilike(topic_name)).first()
                if not topic:
                    topic = ResearchTopic(name=topic_name)
                    db.add(topic)
                    db.flush()
                document.topics.append(topic)
        
        db.commit()
        db.refresh(document)
        
        # Process document
        try:
            result = processor.process_document(file_path, file.filename, document.id)

            extracted_text = result.get("cleaned_text", "")
            first_page_text = "\n".join(page.get("text", "") for page in result.get("page_data", [])[:2])
            metadata_text = extracted_text or first_page_text
            metadata_lower = metadata_text.lower()
            extracted_metadata = result.get("metadata", {})
            if document.author and any(label in document.author.lower() for label in processor.NON_AUTHOR_LABELS):
                document.author = None
            if document.title == original_filename and extracted_metadata.get("title"):
                document.title = str(extracted_metadata["title"]).strip()[:500]
            if not document.author and extracted_metadata.get("author"):
                document.author = str(extracted_metadata["author"]).strip()[:255]
            if not document.authors_json and extracted_metadata.get("authors"):
                document.authors_json = json.dumps(extracted_metadata["authors"])
            if not document.authors_json:
                document.authors_json = json.dumps([document.author])
            if not author_type:
                document.author_type = extracted_metadata.get("author_type") or ("individual" if document.author else "unknown")
            if author_confidence is None:
                document.author_confidence = extracted_metadata.get("author_confidence")
            if not author_source:
                document.author_source = extracted_metadata.get("author_source")
            if not document.publication_year and extracted_metadata.get("publication_year"):
                document.publication_year = extracted_metadata["publication_year"]
            if extracted_metadata.get("publication_period"):
                document.publication_period = extracted_metadata["publication_period"]
                document.publication_year = extracted_metadata.get("publication_year") or document.publication_year
            if department and not document.category:
                document.category = db.query(Category).filter(Category.name == department.strip()).first()
            if not document.category and extracted_metadata.get("department"):
                department_name = str(extracted_metadata["department"]).strip()
                department_name = department_name[:100]
                document.category = db.query(Category).filter(Category.name == department_name).first()
                if not document.category:
                    document.category = Category(name=department_name, description="Extracted document department")
            if not document.category and extracted_metadata.get("category"):
                category_name = str(extracted_metadata["category"]).strip()[:100]
                document.category = db.query(Category).filter(Category.name.ilike(category_name)).first()
                if not document.category:
                    document.category = Category(name=category_name, description="Automatically classified research category")
            if not document.document_type and extracted_metadata.get("document_type"):
                type_name = str(extracted_metadata["document_type"]).strip()[:100]
                document.document_type = db.query(DocumentType).filter(DocumentType.name == type_name).first()
                if not document.document_type:
                    document.document_type = DocumentType(name=type_name, description="Extracted document type")
            for topic_name in extracted_metadata.get("topics", []):
                topic = db.query(ResearchTopic).filter(ResearchTopic.name.ilike(topic_name)).first()
                if not topic:
                    topic = ResearchTopic(name=topic_name)
                    db.add(topic)
                    db.flush()
                if topic not in document.topics:
                    document.topics.append(topic)
            for keyword_name in extracted_metadata.get("keywords", []):
                keyword = db.query(Keyword).filter(Keyword.name.ilike(keyword_name)).first()
                if not keyword:
                    keyword = Keyword(name=keyword_name)
                    db.add(keyword)
                    db.flush()
                if keyword not in document.keywords:
                    document.keywords.append(keyword)
            if not document.category:
                document.category = next((category for category in db.query(Category).filter(Category.is_active.is_(True)).all() if category.name.lower() in metadata_lower), None)
            if not document.document_type:
                document.document_type = next((doc_type for doc_type in db.query(DocumentType).filter(DocumentType.is_active.is_(True)).all() if doc_type.name.lower() in metadata_lower), None)
            if not document.publication_year:
                year_match = re.search(r"\b(19|20)\d{2}\b", metadata_text) or re.search(r"\b(19|20)\d{2}\b", file.filename)
                if year_match:
                    document.publication_year = int(year_match.group(0))
            existing_keywords = db.query(Keyword).all()
            for keyword in existing_keywords:
                if keyword.name.lower() in extracted_text.lower() and keyword not in document.keywords:
                    document.keywords.append(keyword)
            
            # Update document with processing results
            document.is_processed = True
            document.processing_status = "completed"
            document.chunk_count = result['total_chunks']
            for chunk in result.get('chunks', []):
                db.add(DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk['index'],
                    chunk_text=chunk['text'],
                    chunk_length=chunk.get('length', 0),
                    page_number=chunk.get('page_number'),
                ))
            db.commit()

            # Vector indexing is part of processing, but a missing model should
            # leave the durable text search path usable and the failure visible.
            try:
                from app.services.document_service import DocumentService
                embeddings_generated = DocumentService().index_processed_chunks(
                    document_id=document.id,
                    chunks=result.get('chunks', []),
                    db=db,
                )
            except Exception as embedding_error:
                embeddings_generated = 0
                document.processing_error = f"Vector indexing failed: {embedding_error}"
                db.commit()
                logger.warning("Vector indexing failed for document %s: %s", document.id, embedding_error)
            
            log_activity(db, current_user, "Uploaded Document", resource=document.title or original_filename, details=f"Uploaded {original_filename}")
            return {
                "message": "Document uploaded and processed successfully",
                "document_id": document.id,
                "file_name": file.filename,
                "total_chunks": result['total_chunks'],
                "total_characters": result['total_characters'],
                "total_pages": result['total_pages'],
                "embeddings_generated": embeddings_generated,
                "title": document.title,
                "processing_status": document.processing_status,
                "uploaded_by": current_user.username,
            }
            
        except Exception as e:
            db.rollback()
            document = db.query(Document).filter(Document.id == document.id).first()
            if document:
                document.processing_status = "failed"
                document.processing_error = str(e)
                db.commit()
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
    except Exception as e:
        # Clean up file if upload failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/")
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all documents
    """
    documents = db.query(Document).filter(Document.is_active == True).offset(skip).limit(limit).all()
    return {
        "total": len(documents),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "author": doc.author,
                "authors": json.loads(doc.authors_json) if doc.authors_json else ([doc.author] if doc.author else []),
                "author_type": doc.author_type or "unknown",
                "author_confidence": doc.author_confidence,
                "author_source": doc.author_source,
                "metadata_review_status": doc.metadata_review_status or "needs_review",
                "publication_year": doc.publication_year,
                "file_name": doc.file_name,
                "document_name": doc.file_name,
                "file_type": doc.file_type,
                "publication_period": doc.publication_period,
                "department": doc.category.name if doc.category else None,
                "document_type": doc.file_type.upper() if doc.file_type else None,
                "chunk_count": doc.chunk_count,
                "is_processed": doc.is_processed,
                "processing_status": doc.processing_status,
                "processing_error": doc.processing_error,
                "uploaded_by": doc.uploader.username if doc.uploader else None,
                "created_at": doc.created_at
                ,"topics": [topic.name for topic in doc.topics]
                ,"keywords": [keyword.name for keyword in doc.keywords]
            }
            for doc in documents
        ]
    }


@router.get("/saved/list")
async def get_saved_documents(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    saved = db.query(SavedResearch).filter(SavedResearch.user_id == current_user.id).all()
    documents = [db.query(Document).filter(Document.id == item.document_id, Document.is_active.is_(True)).first() for item in saved]
    return {"documents": [{"id": document.id, "title": document.title, "file_name": document.file_name, "author": document.author, "publication_year": document.publication_year, "created_at": document.created_at} for document in documents if document]}
@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get document by ID
    """
    document = db.query(Document).filter(Document.id == document_id, Document.is_active.is_(True)).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "title": document.title,
        "author": document.author,
        "authors": json.loads(document.authors_json) if document.authors_json else ([document.author] if document.author else []),
        "author_type": document.author_type or "unknown",
        "author_confidence": document.author_confidence,
        "author_source": document.author_source,
        "metadata_review_status": document.metadata_review_status or "needs_review",
        "publication_year": document.publication_year,
        "file_name": document.file_name,
        "document_name": document.file_name,
        "file_type": document.file_type,
        "publication_period": document.publication_period,
        "department": document.category.name if document.category else None,
        "document_type": document.file_type.upper() if document.file_type else None,
        "file_size": document.file_size,
        "chunk_count": document.chunk_count,
        "is_processed": document.is_processed,
        "processing_status": document.processing_status,
        "processing_error": document.processing_error,
        "uploaded_by": document.uploader.username if document.uploader else None,
        "created_at": document.created_at
        ,"topics": [topic.name for topic in document.topics]
        ,"keywords": [keyword.name for keyword in document.keywords]
    }


@router.put("/{document_id}/metadata")
async def update_document_metadata(
    document_id: int,
    metadata: DocumentMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_researcher),
):
    document = db.query(Document).filter(Document.id == document_id, Document.is_active.is_(True)).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    title = metadata.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Document title cannot be empty.")
    if metadata.publication_year is not None and not 1900 <= metadata.publication_year <= 2100:
        raise HTTPException(status_code=422, detail="Publication year must be between 1900 and 2100.")

    author = metadata.author.strip()
    document.title = title[:500]
    document.author = author[:255] or None
    document.authors_json = json.dumps([document.author] if document.author else [])
    document.author_source = "Manually entered"
    document.author_confidence = None
    document.metadata_review_status = "reviewed"
    document.publication_year = metadata.publication_year
    document.publication_period = str(metadata.publication_year) if metadata.publication_year else None
    db.commit()
    db.refresh(document)
    log_activity(db, current_user, "Updated Document Metadata", resource=document.title, details=f"Updated metadata for document {document.id}")

    return {
        "id": document.id,
        "title": document.title,
        "author": document.author,
        "authors": json.loads(document.authors_json) if document.authors_json else [],
        "author_source": document.author_source,
        "metadata_review_status": document.metadata_review_status,
        "publication_year": document.publication_year,
        "publication_period": document.publication_period,
    }


@router.get("/{document_id}/view")
async def view_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    document = db.query(Document).filter(Document.id == document_id, Document.is_active.is_(True)).first()
    if not document or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    media_type = "application/pdf" if document.file_type.lower() == "pdf" else "application/octet-stream"
    log_activity(db, current_user, "Viewed Document", resource=document.title or document.file_name, details=f"Viewed document {document.id}")
    return FileResponse(document.file_path, filename=document.file_name, media_type=media_type, content_disposition_type="inline")


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    document = db.query(Document).filter(Document.id == document_id, Document.is_active.is_(True)).first()
    if not document or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    log_activity(db, current_user, "Downloaded Document", resource=document.title or document.file_name, details=f"Downloaded document {document.id}")
    return FileResponse(document.file_path, filename=document.file_name, media_type="application/octet-stream")


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_researcher)
):
    """
    Delete document and its associated chunks
    """
    if current_user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer users cannot delete documents.")
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document.file_path
    document_title = document.title or document.file_name
    try:
        db.query(SavedResearch).filter(SavedResearch.document_id == document.id).delete(synchronize_session=False)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)
        db.delete(document)
        db.commit()
    except Exception as delete_error:
        db.rollback()
        logger.exception("Could not delete document %s from the database", document.id)
        raise HTTPException(status_code=500, detail="Document could not be deleted from the database.") from delete_error

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as file_error:
            logger.warning("Could not remove file for deleted document %s: %s", document.id, file_error)

    try:
        from app.services.vector_store import VectorStore
        VectorStore().delete_document_chunks(document_id=document.id)
    except Exception as vector_error:
        logger.warning("Could not remove vectors for document %s: %s", document.id, vector_error)

    log_activity(db, current_user, "Deleted Document", resource=document_title, details=f"Deleted document {document.id}")
    
    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/save")
async def save_document(document_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id, Document.is_active.is_(True)).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    saved = db.query(SavedResearch).filter(SavedResearch.user_id == current_user.id, SavedResearch.document_id == document_id).first()
    if not saved:
        db.add(SavedResearch(user_id=current_user.id, document_id=document_id))
        db.commit()
        log_activity(db, current_user, "Saved Document", resource=document.title or document.file_name, details=f"Saved document {document.id}")
    return {"saved": True, "document_id": document_id}


@router.delete("/{document_id}/save")
async def unsave_document(document_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    saved = db.query(SavedResearch).filter(SavedResearch.user_id == current_user.id, SavedResearch.document_id == document_id).first()
    if saved:
        db.delete(saved)
        db.commit()
        document = db.query(Document).filter(Document.id == document_id).first()
        log_activity(db, current_user, "Unsaved Document", resource=document.title or document.file_name if document else str(document_id), details=f"Removed saved document {document_id}")
    return {"saved": False, "document_id": document_id}