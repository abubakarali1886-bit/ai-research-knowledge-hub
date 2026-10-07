"""
Document Service - Manages document processing with embeddings
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.document_processor import DocumentProcessor
from app.models.document import Document, DocumentChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents with embeddings"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.embedding_service = None
        self.vector_store = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize embedding and vector services"""
        try:
            from app.services.embedding_service import EmbeddingService
            from app.services.vector_store import VectorStore
            self.embedding_service = EmbeddingService()
            self.vector_store = VectorStore()
            logger.info("DocumentService initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    def process_document_with_embeddings(
        self,
        file_path: str,
        filename: str,
        document_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process a document, generate embeddings, and store in vector database
        """
        logger.info(f"Processing document {document_id} with embeddings")
        
        # Step 1: Process the document (extract, clean, chunk)
        result = self.processor.process_document(file_path, filename, document_id)
        
        if result['total_chunks'] == 0:
            logger.warning(f"No chunks created for document {document_id}")
            return result
        
        # Step 2: Generate embeddings for all chunks
        chunk_texts = [chunk['text'] for chunk in result['chunks']]
        embeddings = self.embedding_service.generate_embeddings(chunk_texts)
        
        if not embeddings:
            logger.error(f"No embeddings generated for document {document_id}")
            result['error'] = "Embedding generation failed"
            return result
        
        # Step 3: Store in ChromaDB
        self.vector_store.delete_document_chunks(document_id=document_id)
        self.vector_store.add_document_chunks(
            document_id=document_id,
            chunks=result['chunks'],
            embeddings=embeddings
        )
        
        # Step 4: Replace stale chunk references in PostgreSQL
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
        for i, chunk in enumerate(result['chunks']):
            chunk_record = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk['index'],
                chunk_text=chunk['text'],
                chunk_length=chunk.get('length', 0),
                page_number=chunk.get('page_number'),
                chroma_id=f"doc_{document_id}_chunk_{chunk['index']}"
            )
            db.add(chunk_record)
        
        db.commit()
        
        # Step 5: Update document status
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.is_processed = True
            document.processing_status = "completed"
            document.chunk_count = len(result['chunks'])
            db.commit()
        
        result['embeddings_generated'] = len(embeddings)
        logger.info(f"Successfully processed document {document_id} with {len(embeddings)} embeddings")
        
        return result

    def index_processed_chunks(self, document_id: int, chunks: List[Dict[str, Any]], db: Session) -> int:
        """Index already-persisted chunks without creating duplicate database rows."""
        if not chunks:
            return 0
        embeddings = self.embedding_service.generate_embeddings([chunk['text'] for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise RuntimeError("Embedding count did not match chunk count")
        self.vector_store.delete_document_chunks(document_id=document_id)
        self.vector_store.add_document_chunks(document_id=document_id, chunks=chunks, embeddings=embeddings)
        records = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
        by_index = {chunk['index']: chunk for chunk in chunks}
        for record in records:
            if record.chunk_index in by_index:
                record.chroma_id = f"doc_{document_id}_chunk_{record.chunk_index}"
        db.commit()
        return len(embeddings)
    
    def search_documents(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks using semantic search
        """
        if not query:
            logger.warning("Empty query provided")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []
        
        # Search in ChromaDB
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        return results