"""
LLM Service - Handles communication with Ollama and DeepSeek
"""
import logging
import requests
from typing import List, Dict, Any, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with local LLM via Ollama"""
    
    def __init__(self, model_name: str = None, host: str = None):
        """
        Initialize LLM service
        """
        self.model_name = model_name or os.getenv("LLM_MODEL", "deepseek-r1:1.5b")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.api_url = f"{self.host}/api/generate"
        
        # Check if Ollama is running
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                if self.model_name not in str(model_names):
                    logger.warning(f"Model '{self.model_name}' not found in Ollama. Available: {model_names}")
                else:
                    logger.info(f"Ollama is running. Model '{self.model_name}' available.")
            else:
                logger.warning(f"Ollama responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama is not running. Please start Ollama with: ollama serve")
        except Exception as e:
            logger.warning(f"Error checking Ollama: {e}")
    
    def generate_response(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate a response using the LLM with context
        """
        # Build the system prompt
        system_prompt = self._build_rag_prompt(context)
        
        # Build the full prompt
        full_prompt = f"{system_prompt}\n\nQuestion: {prompt}\n\nAnswer:"
        
        # Prepare request
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "think": False,
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            }
        }
        
        try:
            logger.info(f"Sending request to Ollama: {self.model_name}")
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300  # Longer timeout for LLM
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = self._clean_answer(result.get('response', ''))
                
                # Clean up the answer (remove any extra text)
                if not answer:
                    return {
                        "success": False,
                        "error": "The AI service returned an empty response. Please try again.",
                    }
                
                return {
                    "success": True,
                    "answer": answer,
                    "model": self.model_name,
                    "tokens_generated": result.get('eval_count', 0)
                }
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Ollama returned status {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return {
                "success": False,
                "error": "Request timed out. The model might be too slow."
            }
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama")
            return {
                "success": False,
                "error": "Cannot connect to Ollama. Make sure it's running with: ollama serve"
            }
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_rag_prompt(self, context: str) -> str:
        """
        Build the RAG system prompt with context
        """
        return f"""You are a knowledgeable research assistant specializing in central banking and economic policy.

You MUST base your answer ONLY on the provided context below. 

If the context does not contain enough information to answer the question, say: "The available documents do not provide enough information to answer this question."

Do not make up information. Do not use your own knowledge. Only use the context provided.

CONTEXT:
{context}

Instructions:
1. Read the context carefully
2. Answer the question using ONLY the context
3. If the context doesn't have the answer, say so
4. Be concise but comprehensive
5. Use professional language
6. Cite specific information from the context when possible"""
    
    def _clean_answer(self, answer: str) -> str:
        """
        Clean the answer from the LLM
        """
        # Remove the optional reasoning block emitted by DeepSeek.
        if "<think>" in answer.lower():
            if "</think>" not in answer.lower():
                return ""
            answer = answer.split("</think>", 1)[-1]

        answer = answer.replace("<think>", "").replace("</think>", "")
        
        # Remove extra whitespace
        answer = answer.strip()
        
        return answer
    
