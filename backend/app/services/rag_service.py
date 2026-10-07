"""
RAG Service - Retrieval-Augmented Generation
"""
import logging
from typing import Dict, Any, List, Optional

from app.services.document_service import DocumentService
from app.services.llm_service import LLMService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation"""
    
    def __init__(self):
        self.document_service = DocumentService()
        self.llm_service = LLMService()
    
    def answer_question(
        self,
        question: str,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG
        """
        if not question:
            return {
                "success": False,
                "error": "Question cannot be empty"
            }
        
        try:
            # Step 1: Search for relevant chunks
            logger.info(f"Searching for relevant chunks for: {question[:100]}...")
            search_results = self.document_service.search_documents(
                query=question,
                top_k=top_k
            )
            
            if not search_results:
                return {
                    "success": False,
                    "answer": "No relevant documents found in the knowledge base.",
                    "sources": [],
                    "error": "No relevant chunks found"
                }
            
            # Step 2: Build context from chunks
            context = self._build_context(search_results)
            
            # Step 3: Generate answer using LLM
            logger.info("Generating answer with LLM...")
            response = self.llm_service.generate_response(
                prompt=question,
                context=context,
                max_tokens=800,
                temperature=0.2,
            )
            
            if not response['success']:
                return {
                    "success": False,
                    "error": response.get('error', 'LLM generation failed'),
                    "sources": self._extract_sources(search_results) if include_sources else []
                }
            
            # Step 4: Extract sources
            sources = self._extract_sources(search_results) if include_sources else []
            
            return {
                "success": True,
                "question": question,
                "answer": response['answer'],
                "sources": sources,
                "chunks_used": len(search_results),
                "model": response.get('model', 'unknown'),
                "tokens_generated": response.get('tokens_generated', 0)
            }
            
        except Exception as e:
            logger.error(f"Error in RAG service: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_context(self, search_results: List[Dict]) -> str:
        """
        Build context from search results
        """
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            # Format each chunk with source info
            chunk_text = result.get('document', '')
            metadata = result.get('metadata', {})
            distance = result.get('distance', 0)
            
            # Add source identifier
            source_id = metadata.get('document_id', 'Unknown')
            chunk_index = metadata.get('chunk_index', 0)
            
            context_parts.append(
                f"[Source {source_id}, Chunk {chunk_index}, Relevance: {1 - distance:.3f}]\n"
                f"{chunk_text}\n"
            )
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Extract source information from search results
        """
        sources = []
        
        for result in search_results:
            metadata = result.get('metadata', {})
            
            source = {
                "document_id": metadata.get('document_id'),
                "chunk_index": metadata.get('chunk_index'),
                "page_number": metadata.get('page_number'),
                "relevance_score": 1 - result.get('distance', 1),  # Convert distance to similarity
                "excerpt": result.get('document', '')[:500]  # First 500 chars
            }
            sources.append(source)
        
        return sources