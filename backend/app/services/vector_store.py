"""
Vector Store Service - Manages ChromaDB operations
"""
import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Service for managing vector database operations with ChromaDB"""
    
    def __init__(self, persist_directory: str = "vectorstore"):
        """
        Initialize ChromaDB client
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.persist_directory = os.path.abspath(os.path.join(project_root, persist_directory)) if not os.path.isabs(persist_directory) else persist_directory
        
        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        logger.info(f"ChromaDB initialized with persistence at: {self.persist_directory}")
    
    def get_or_create_collection(self, collection_name: str = "research_documents"):
        """
        Get or create a collection
        """
        try:
            collection = self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' found")
        except:
            collection = self.client.create_collection(collection_name)
            logger.info(f"Collection '{collection_name}' created")
        
        return collection
    
    def add_document_chunks(
        self,
        document_id: int,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        collection_name: str = "research_documents"
    ):
        """
        Add document chunks with embeddings to ChromaDB
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings to add")
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) doesn't match embeddings count ({len(embeddings)})")
        
        collection = self.get_or_create_collection(collection_name)
        
        # Prepare data for ChromaDB
        ids = [f"doc_{document_id}_chunk_{chunk['index']}" for chunk in chunks]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [
            {
                'document_id': document_id,
                'chunk_index': chunk['index'],
                'chunk_length': chunk.get('length', 0),
                'page_number': chunk.get('page_number', 1)
            }
            for chunk in chunks
        ]
        
        # Upsert keeps retries idempotent and prevents duplicate vector records.
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(chunks)} chunks to ChromaDB for document {document_id}")
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: str = "research_documents"
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using query embedding
        """
        collection = self.get_or_create_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results and results['ids']:
            for i, doc_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': doc_id,
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
        
        return formatted_results
    
    def delete_document_chunks(self, document_id: int, collection_name: str = "research_documents"):
        """
        Delete all chunks for a specific document
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # Get all IDs for this document
            results = collection.get(
                where={"document_id": document_id}
            )
            
            if results and results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            
            logger.info(f"No chunks found for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document chunks: {e}")
            return False
    
    def get_collection_count(self, collection_name: str = "research_documents") -> int:
        """
        Get total number of chunks in a collection
        """
        collection = self.get_or_create_collection(collection_name)
        return collection.count()