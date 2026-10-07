"""
Summarization Service - Generates AI summaries of documents
"""
import logging
import os
import re
import requests
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.document_processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for generating document summaries using AI"""
    
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("SUMMARY_LLM_MODEL", "qwen3.5:0.8b")
        self.api_url = f"{self.host}/api/generate"
    
    def summarize_document(
        self,
        document_id: int,
        db: Session,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate a summary for a document
        """
        logger.info(f"Summarizing document {document_id}")
        
        # Step 1: Get document from database
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {
                "success": False,
                "error": f"Document {document_id} not found"
            }
        
        if not document.is_processed:
            return {
                "success": False,
                "error": "Document has not been processed yet"
            }
        
        # Step 2: Get all chunks for the document
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        if not chunks:
            try:
                processed = DocumentProcessor().process_document(document.file_path, document.file_name, document.id)
                chunks = [DocumentChunk(document_id=document.id, chunk_index=chunk['index'], chunk_text=chunk['text'], chunk_length=chunk.get('length', 0)) for chunk in processed.get('chunks', [])]
                db.add_all(chunks)
                db.commit()
            except Exception as processing_error:
                logger.error("Could not extract chunks for summary: %s", processing_error)
                return {"success": False, "error": "No processed research content is available for this document"}
            if not chunks:
                return {"success": False, "error": "No processed research content is available for this document"}
        
        # Step 3: Combine chunks into full text
        full_text = " ".join([chunk.chunk_text for chunk in chunks])
        
        # Step 4: Keep a broad evidence window while avoiding prompt overflow.
        if len(full_text) > 18000:
            full_text = full_text[:18000] + "..."
        
        logger.info(f"Text length: {len(full_text)} characters")
        
        # Step 5: Generate summary
        summary_result = self._generate_summary(
            full_text,
            max_tokens,
            temperature,
            document_title=document.title or document.file_name,
            author=document.author,
            publication_year=document.publication_year,
            publication_period=document.publication_period,
            file_name=document.file_name,
        )
        
        if not summary_result['success']:
            return summary_result
        
        # Step 6: Structure the summary
        structured_summary = self._structure_summary(summary_result['summary'])
        structured_summary.update({
            "report_title": document.title or document.file_name,
            "report_source": self._format_source_label(document.file_name, document.publication_year, document.publication_period),
            "report_authors": document.author or "Institutional publication",
        })
        
        return {
            "success": True,
            "document_id": document_id,
            "document_title": document.title or document.file_name,
            "summary": structured_summary,
            "raw_summary": summary_result['summary'],
            "total_chunks": len(chunks),
            "total_characters": len(full_text)
        }
    
    def _generate_summary(
        self,
        text: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        document_title: str = "",
        author: Optional[str] = None,
        publication_year: Optional[int] = None,
        publication_period: Optional[str] = None,
        file_name: str = "",
    ) -> Dict[str, Any]:
        """
        Generate summary using LLM directly via Ollama API
        """
        source_label = self._format_source_label(file_name, publication_year, publication_period)
        prompt = f"""You are the senior research editor of a central bank or major public research institution. Prepare a publication-quality institutional research brief from the source text below. The result will be read by policymakers, economists, senior management, and researchers.

    Evidence rules:
    - Use only information explicitly supported by the source text.
    - Do not invent statistics, dates, institutions, methods, findings, recommendations, or causal claims.
    - Preserve qualifications such as 'may', 'suggests', and 'is associated with'.
    - If a section is not supported, write exactly: Not stated in the source document.
    - Distinguish reported findings from editorial interpretation.

    Output only the research brief below. Start with the first heading and do not add an introduction, preamble, sign-off, or commentary before or after it. Return exactly this format, in this order:
    # RESEARCH SUMMARY
    ## {document_title}
    **Source:** {source_label}
    **Authors:** {author or 'Institutional publication'}

    ### 1. Executive Summary
    ### 2. Research Objective and Scope
    ### 3. Methodology and Data
    ### 4. Principal Findings
    ### 5. Economic, Sectoral, Fiscal or Welfare Effects
    ### 6. Constraints and Risks
    ### 7. Policy Implications
    ### 8. Conclusion
    ### 9. Limitations and Evidence Gaps

    Writing standard:
    - Write an analytical institutional brief, not a conversational answer to a question. The brief itself must be the answer; do not describe what you are going to do or how you produced it.
    - Begin the Executive Summary with the central issue and principal conclusion as direct factual statements. Never address the reader or narrate the document: do not use conversational openings such as "Okay, let me explain", "I'm trying to understand", or "Let me break that down", or source-led wording such as "the document says", "the report discusses", or "the study explains".
    - Write subject-first analytical claims: state the supported finding itself, rather than saying what the document, report, author, or study says about it. For example, use "[Subject] [supported finding]" rather than "The document explains that [subject] [finding]." Avoid first-person wording, questions, advice to the reader, and AI/meta phrases such as "Here is the summary" or "As an AI".
    - Except for the title, metadata labels, and the exact unsupported-section response, do not mention or narrate the document, report, source, author, or study. Keep each section to no more than two concise sentences.
    - Every factual claim must be directly supported by the source. Do not infer that a trend is significant, identify causes or economic effects, invent a research objective, or recommend policy action unless the source explicitly supports it. If evidence for a requested section is absent, write exactly: Not stated in the source document.
    - Do not include private reasoning, drafting notes, or text inside <think> tags in the output.
    - Use concise, well-organized paragraphs with clear topic sentences. Use bullets for multiple distinct findings, recommendations, risks, or evidence gaps; never use dialogue, greetings, questions, or first-person language.
    - State the research question or objective, data sources, study period, sample, analytical method, and limitations when the source provides them.
    - Separate empirical findings from interpretation and policy implications. Do not turn findings into recommendations unless the source supports that interpretation.
    - Include exact figures, years, sectors, methods, and named institutions only when they appear in the source.
    - If a section is unsupported, write exactly: Not stated in the source document.
    - Do not mention the prompt, the source text as an input, the model, artificial intelligence, or the act of summarising.

    Write in formal, neutral institutional English with precise terminology and complete sentences. Avoid repetition and generic filler.

    SOURCE DOCUMENT:
    {text}

    INSTITUTIONAL BRIEFING:"""
        
        try:
            logger.info(f"Sending request to Ollama with model: {self.model}")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": min(max(max_tokens, 1000), 1600),
                    "top_p": 0.9
                }
                ,"think": False
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
                logger.info(f"Summary length: {len(summary)} characters")
                
                if not summary:
                    return {
                        "success": False,
                        "error": "Ollama returned empty response"
                    }
                
                summary = self._clean_summary_response(summary)
                
                return {
                    "success": True,
                    "summary": summary
                }
            else:
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"Ollama returned status {response.status_code}: {response.text[:200]}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return {
                "success": False,
                "error": "Request timed out. The document may be too long or the model is slow."
            }
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama")
            return {
                "success": False,
                "error": "Cannot connect to Ollama. Make sure it's running with: ollama serve"
            }
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _format_source_label(
        file_name: str,
        publication_year: Optional[int] = None,
        publication_period: Optional[str] = None,
    ) -> str:
        clean_name = os.path.splitext(file_name or "Research document")[0]
        clean_name = clean_name.replace("_", " ").strip()
        suffix = publication_period or publication_year
        return f"{clean_name}, {suffix}" if suffix else clean_name

    @staticmethod
    def _clean_summary_response(summary: str) -> str:
        summary = re.sub(r"<think>.*?(?:</think>|$)", "", summary, flags=re.IGNORECASE | re.DOTALL).strip()
        heading = re.search(r"^#\s*RESEARCH SUMMARY\s*$", summary, flags=re.IGNORECASE | re.MULTILINE)
        if heading:
            summary = summary[heading.start():]
        elif summary.startswith("Text:"):
            summary = summary.removeprefix("Text:").strip()
        return summary.strip()

    def _structure_summary(self, raw_summary: str) -> Dict[str, str]:
        """
        Structure the raw summary into sections
        """
        sections = {
            "executive_summary": "",
            "research_objective": "",
            "methodology": "",
            "key_findings": "",
            "main_conclusions": "",
            "policy_implications": "",
            "limitations": "",
            "effects": "",
            "constraints": "",
        }
        
        # If summary is empty, return empty sections
        if not raw_summary:
            return sections
        
        heading_map = {
            '1. OVERVIEW': 'executive_summary',
            '1. EXECUTIVE SUMMARY': 'executive_summary',
            '2. OBJECTIVES OF THE STUDY': 'research_objective',
            '2. RESEARCH OBJECTIVE AND SCOPE': 'research_objective',
            '3. METHODOLOGY': 'methodology',
            '3. METHODOLOGY AND DATA': 'methodology',
            '4. KEY FINDINGS': 'key_findings',
            '4. PRINCIPAL FINDINGS': 'key_findings',
            '5. TRADE, SECTORAL, FISCAL OR WELFARE EFFECTS': 'effects',
            '5. ECONOMIC, SECTORAL, FISCAL OR WELFARE EFFECTS': 'effects',
            '6. PRIVATE-SECTOR EXPERIENCE AND KEY CONSTRAINTS': 'constraints',
            '6. CONSTRAINTS AND RISKS': 'constraints',
            '7. POLICY IMPLICATIONS': 'policy_implications',
            '8. CONCLUSION': 'main_conclusions',
            '9. LIMITATIONS AND EVIDENCE GAPS': 'limitations',
            'EXECUTIVE SUMMARY': 'executive_summary',
            'RESEARCH OBJECTIVE': 'research_objective',
            'CONTEXT AND APPROACH': 'methodology',
            'KEY FINDINGS': 'key_findings',
            'CONCLUSIONS': 'main_conclusions',
            'IMPLICATIONS AND RECOMMENDATIONS': 'policy_implications',
            'LIMITATIONS': 'limitations',
        }
        current_section = None
        for line in raw_summary.splitlines():
            normalized = line.strip().strip('#*:').strip().upper()
            if normalized in heading_map:
                current_section = heading_map[normalized]
                continue
            if current_section and line.strip():
                sections[current_section] = f"{sections[current_section]} {line.strip()}".strip()

        if not any(sections.values()):
            sections['executive_summary'] = raw_summary.strip()
        
        return sections
    
