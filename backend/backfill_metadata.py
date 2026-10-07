"""Backfill automatic metadata, topics, and categories for existing documents."""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.document import Category, Document, DocumentType, Keyword, ResearchTopic
from app.services.document_processor import DocumentProcessor


def get_or_create(db, model, name, **defaults):
    if not name:
        return None
    record = db.query(model).filter(model.name.ilike(name)).first()
    if not record:
        record = model(name=name, **defaults)
        db.add(record)
        db.flush()
    return record


def backfill_metadata():
    db = SessionLocal()
    processor = DocumentProcessor()
    updated = 0
    failed = 0
    try:
        documents = db.query(Document).filter(Document.is_active.is_(True)).all()
        for document in documents:
            try:
                if not document.file_path or not os.path.exists(document.file_path):
                    continue
                result = processor.process_document(document.file_path, document.file_name, document.id)
                metadata = result.get("metadata", {})
                if (not document.title or document.title == document.file_name or document.title.lower() in {"bank of tanzania", "the bank of tanzania", "government of tanzania"}) and metadata.get("title"):
                    document.title = metadata["title"][:500]
                resolved_author = str(metadata["author"]).strip()[:255] if metadata.get("author") else None
                document.author = resolved_author
                document.authors_json = json.dumps(metadata.get("authors") or [])
                document.author_type = metadata.get("author_type") or "unknown"
                document.author_confidence = metadata.get("author_confidence")
                document.author_source = metadata.get("author_source")
                document.metadata_review_status = metadata.get("metadata_review_status") or "reviewed"
                if not document.publication_year and metadata.get("publication_year"):
                    document.publication_year = metadata["publication_year"]
                if metadata.get("publication_period"):
                    document.publication_period = metadata["publication_period"]
                    document.publication_year = metadata.get("publication_year") or document.publication_year
                if metadata.get("category"):
                    document.category = get_or_create(db, Category, metadata["category"], description="Automatically classified research category")
                if metadata.get("document_type"):
                    document.document_type = get_or_create(db, DocumentType, metadata["document_type"], description="Automatically classified document type")
                for topic_name in metadata.get("topics", []):
                    topic = get_or_create(db, ResearchTopic, topic_name)
                    if topic and topic not in document.topics:
                        document.topics.append(topic)
                for keyword_name in metadata.get("keywords", []):
                    keyword = get_or_create(db, Keyword, keyword_name)
                    if keyword and keyword not in document.keywords:
                        document.keywords.append(keyword)
                updated += 1
                db.commit()
            except Exception as error:
                failed += 1
                db.rollback()
                print(f"Failed document {document.id}: {error}")
        print(f"Backfill complete: updated={updated}, failed={failed}")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_metadata()
