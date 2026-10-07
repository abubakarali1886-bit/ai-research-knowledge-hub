"""
Script to process an existing document with embeddings
"""
import sys
import os
from sqlalchemy.orm import Session

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import SessionLocal
from app.models.document import Document
from app.services.document_service import DocumentService


def process_document(document_id: int):
    """
    Process a document and generate embeddings
    """
    db = SessionLocal()
    
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"❌ Document {document_id} not found")
            return
        
        print(f"📄 Processing document: {document.file_name}")
        print(f"   ID: {document.id}")
        print(f"   Path: {document.file_path}")
        print(f"   Status: {document.processing_status}")
        
        # Initialize document service
        service = DocumentService()
        
        # Process document with embeddings
        result = service.process_document_with_embeddings(
            file_path=document.file_path,
            filename=document.file_name,
            document_id=document.id,
            db=db
        )
        
        print(f"\n✅ Document processed successfully!")
        print(f"   Total chunks: {result['total_chunks']}")
        print(f"   Total characters: {result['total_characters']}")
        print(f"   Embeddings generated: {result.get('embeddings_generated', 0)}")
        
        # Verify in ChromaDB
        from app.services.vector_store import VectorStore
        vector_store = VectorStore()
        count = vector_store.get_collection_count()
        print(f"   Total chunks in vector database: {count}")
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Process document ID 1 (the one we uploaded)
    process_document(1)