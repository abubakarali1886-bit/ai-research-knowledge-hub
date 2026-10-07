"""Import files already present in data/documents into the database."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.document import Category, Document, DocumentChunk, DocumentType, Keyword, ResearchTopic
from app.services.document_processor import DocumentProcessor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCUMENT_DIR = os.path.join(PROJECT_ROOT, "data", "documents")


def get_or_create(db, model, name, **defaults):
    if not name:
        return None
    record = db.query(model).filter(model.name.ilike(name)).first()
    if not record:
        record = model(name=name, **defaults)
        db.add(record)
        db.flush()
    return record


def import_documents():
    db = SessionLocal()
    processor = DocumentProcessor()
    imported = 0
    skipped = 0
    try:
        for filename in sorted(os.listdir(DOCUMENT_DIR)):
            if not filename.lower().endswith((".pdf", ".docx")):
                continue
            path = os.path.join(DOCUMENT_DIR, filename)
            if not os.path.isfile(path):
                continue
            if db.query(Document).filter(Document.file_name == filename, Document.is_active.is_(True)).first():
                skipped += 1
                continue
            try:
                result = processor.process_document(path, filename, 0)
                metadata = result.get("metadata", {})
                document = Document(
                    title=(metadata.get("title") or filename)[:500],
                    author=str(metadata.get("author"))[:255] if metadata.get("author") else None,
                    publication_year=metadata.get("publication_year"),
                    publication_period=metadata.get("publication_period"),
                    file_path=path,
                    file_name=filename,
                    file_size=os.path.getsize(path),
                    file_type=os.path.splitext(filename)[1].lstrip(".").lower(),
                    is_processed=True,
                    processing_status="completed" if result.get("total_chunks") else "failed",
                    processing_error=None if result.get("total_chunks") else "No text could be extracted",
                    chunk_count=result.get("total_chunks", 0),
                )
                db.add(document)
                db.flush()
                if metadata.get("category"):
                    document.category = get_or_create(db, Category, metadata["category"], description="Automatically classified research category")
                if metadata.get("document_type"):
                    document.document_type = get_or_create(db, DocumentType, metadata["document_type"], description="Automatically classified document type")
                for topic_name in metadata.get("topics", []):
                    topic = get_or_create(db, ResearchTopic, topic_name)
                    if topic not in document.topics:
                        document.topics.append(topic)
                for keyword_name in metadata.get("keywords", []):
                    keyword = get_or_create(db, Keyword, keyword_name)
                    if keyword not in document.keywords:
                        document.keywords.append(keyword)
                for chunk in result.get("chunks", []):
                    db.add(DocumentChunk(document_id=document.id, chunk_index=chunk["index"], chunk_text=chunk["text"], chunk_length=chunk.get("length", 0), page_number=chunk.get("page_number"), chroma_id=f"doc_{document.id}_chunk_{chunk['index']}"))
                db.commit()
                imported += 1
            except Exception as error:
                db.rollback()
                print(f"Failed {filename}: {error}")
        print(f"Import complete: imported={imported}, skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    import_documents()
