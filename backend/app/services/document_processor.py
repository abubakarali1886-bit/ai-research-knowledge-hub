"""
Document Processing Service - Handles PDF and DOCX extraction
"""
import os
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pypdf as PyPDF2
import pdfplumber
from docx import Document as DocxDocument
from app.models.document import Document

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing uploaded documents"""
    
    # Allowed file types
    ALLOWED_TYPES = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    # Maximum file size (50 MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Chunk size for text splitting (characters)
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    TOPIC_RULES = {
        'Monetary Policy': ('monetary policy', 'policy rate', 'interest rate', 'central bank'),
        'Price Stability and Inflation': ('inflation', 'consumer price', 'price stability', 'price level'),
        'Exchange Rates and International Economics': ('exchange rate', 'foreign exchange', 'balance of payments', 'current account'),
        'Macroeconomics': ('macroeconomic', 'gross domestic product', 'gdp', 'economic outlook'),
        'Financial Stability': ('financial stability', 'systemic risk', 'financial stress', 'prudential'),
        'Banking Supervision': ('bank supervision', 'capital adequacy', 'commercial bank', 'banking regulation'),
        'Payment Systems': ('payment system', 'electronic payment', 'settlement system', 'mobile money'),
        'Financial Inclusion': ('financial inclusion', 'access to finance', 'financial literacy', 'unbanked'),
        'Fiscal Policy and Public Finance': ('fiscal policy', 'government revenue', 'public debt', 'government expenditure'),
        'Economic Growth': ('economic growth', 'productivity', 'employment', 'economic development'),
        'Government Finance and Securities': ('government securities', 'treasury bond', 'treasury bills', 'government debt', 'public debt'),
        'Foreign Exchange and Reserves': ('foreign exchange', 'bureau de change', 'interbank foreign exchange', 'foreign reserves'),
        'Banking and Microfinance': ('banking sector', 'microfinance', 'deposit insurance', 'credit reference', 'bank licence'),
        'Currency and Cash Management': ('banknotes', 'bank notes', 'coins', 'currency issuance', 'cash management'),
        'Consumer Protection': ('consumer protection', 'customer complaints', 'financial consumer', 'consumer rights'),
        'Financial Technology and Digital Finance': ('fintech', 'digital lending', 'digital currency', 'mobile money', 'regulatory sandbox'),
        'Anti-Money Laundering': ('anti-money laundering', 'money laundering', 'aml', 'terrorist financing'),
        'Housing Finance': ('mortgage market', 'housing finance', 'mortgage financing'),
    }
    CATEGORY_RULES = {
        'Monetary Policy': ('monetary policy', 'policy rate', 'interest rate', 'inflation', 'price stability'),
        'Financial Stability': ('financial stability', 'systemic risk', 'financial stress', 'prudential'),
        'Banking Supervision': ('bank supervision', 'capital adequacy', 'commercial bank', 'banking regulation'),
        'Payment Systems': ('payment system', 'electronic payment', 'settlement system', 'mobile money'),
        'Financial Deepening and Inclusion': ('financial inclusion', 'financial deepening', 'access to finance', 'financial literacy', 'unbanked'),
        'Macroeconomics': ('macroeconomic', 'gross domestic product', 'gdp', 'economic outlook', 'economic growth'),
        'Financial Markets': ('financial market', 'treasury bond', 'treasury bills', 'foreign exchange', 'government securities'),
        'Currency and Banking Services': ('banknotes', 'bank notes', 'coins', 'currency issuance', 'banking services'),
        'Financial Deepening and Inclusion': ('financial inclusion', 'financial deepening', 'consumer protection', 'financial literacy'),
    }
    DOCUMENT_TYPE_RULES = {
        'Working Paper': ('working paper', 'working papers'),
        'Research Report': ('research report', 'research reports'),
        'Strategic Plan': ('strategic plan', 'strategic plans'),
        'Financial Stability Report': ('financial stability report',),
        'Framework': ('framework',),
        'Monetary Policy Report': ('monetary policy report',),
        'Monetary Policy Statement': ('monetary policy statement',),
        'Annual Report': ('annual report',),
        'Monthly Economic Review': ('monthly economic review',),
        'Weekly Financial Markets Report': ('weekly financial markets report', 'financial markets weekly report'),
        'Quarterly Economic Bulletin': ('quarterly economic bulletin',),
        'Statistical Report': ('statistical report', 'statistical bulletin'),
        'Policy Brief': ('policy brief',),
        'Speech': ('speech', 'remarks'),
        'Public Notice': ('public notice', 'notice to the public', 'taarifa kwa umma', 'tangazo kwa umma'),
        'Press Release': ('press release', 'press statement', 'taarifa kwa vyombo vya habari'),
        'Statement': ('statement', 'communique', 'communiqué'),
        'Circular': ('circular',),
        'Regulation': ('regulation', 'regulations', 'kanuni'),
        'Guideline': ('guideline', 'guidelines', 'mwongozo'),
        'Procedure': ('procedure', 'procedures'),
        'Rule': ('rule', 'rules'),
        'Agreement': ('agreement',),
        'Code of Conduct': ('code of conduct',),
        'Statistical Bulletin': ('statistical bulletin', 'economic statistics'),
        'Statistics Release': ('statistics', 'statistical release', 'data release'),
        'Survey': ('survey',),
        'Calendar': ('issuance calendar', 'calendar'),
        'Tender': ('tender', 'auction call'),
        'Form': ('claim form', 'application form', 'various forms'),
        'Newsletter': ('newsletter', 'jarida'),
    }
    NON_AUTHOR_LABELS = (
        'bank staff', 'bank of tanzania', 'banktanzania', 'editorial team', 'research team', 'acknowledg',
        'supervisor', 'research department', 'department', 'unit', 'directorate', 'division', 'institution',
        'research department and policy', 'prepared by', 'written by', 'study by', 'authors', 'author'
    )
    
    @staticmethod
    def clean_title_text(value: Optional[str]) -> Optional[str]:
        """Normalize a document title without inventing publication wording."""
        if value is None:
            return None
        cleaned = str(value).strip()
        cleaned = re.sub(r'^\d{8}_\d{6}_[0-9a-f]{32}_', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace('_', ' ')
        cleaned = re.sub(r'\.(pdf|docx|doc|xlsx?)$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*[-–—]\s*', ' - ', cleaned)
        cleaned = cleaned.strip(' .:-_')
        cleaned = re.sub(r'\s+([,.;:])', r'\1', cleaned)
        return cleaned or None

    @classmethod
    def extract_author_candidates(cls, text: str) -> List[str]:
        """Extract a list of likely author names while rejecting institutions and labels."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        author_names: List[str] = []
        labels = ('author', 'authors', 'by', 'prepared by', 'written by', 'researcher', 'researchers', 'research team', 'prepared and written by', 'study by')
        skip_until_line = -1

        # BOT working papers often print several authors on the same cover line
        # as the title instead of using an Author label.
        cover_text = '\n'.join(lines[:25])
        person_patterns = (
            r"\b[A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+\b",
            r"\b[A-Z]\.\s*[A-Z][a-z]+\b",
        )
        for line in lines[:25]:
            if not re.search(r'(?i)working paper|wp no|research paper|study', line) and len(re.findall(r"[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+", line)) < 2:
                continue
            if re.search(r'(?i)^working paper series$', line.strip()):
                continue
            grouped_names = re.findall(
                r"[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+)+",
                line,
            )
            for group in grouped_names:
                author_names.extend(re.findall(r"[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+", group))
                line = line.replace(group, '')
            for pattern in person_patterns:
                for match in re.finditer(pattern, line):
                    candidate = match.group(0).strip(' ,;:')
                    if candidate.lower() not in {'working paper', 'research paper', 'working paper series'}:
                        author_names.append(candidate)

        for index, line in enumerate(lines):
            if index < skip_until_line:
                continue
            if re.search(r'(?i)\b(?:message from|chairperson|chairman|director general|governor|deputy governor)\b', line):
                skip_until_line = min(len(lines), index + 2)
                continue
            lower = line.lower()
            if any(lower == label or lower.startswith(f"{label}:") for label in labels):
                range_end = min(len(lines), index + 6)
                for candidate in lines[index + 1:range_end]:
                    candidate_clean = candidate.strip().strip(',:;')
                    if not candidate_clean or len(candidate_clean) < 3:
                        continue
                    if any(token in candidate_clean.lower() for token in ('department', 'directorate', 'division', 'team', 'unit', 'ministry', 'bank', 'institution', 'institute', 'committee')):
                        continue
                    if any(label in candidate_clean.lower() for label in cls.NON_AUTHOR_LABELS):
                        continue
                    if re.search(r'\d', candidate_clean):
                        continue
                    if len(candidate_clean.split()) <= 6 and re.fullmatch(r'[A-Z][A-Za-z\'’.-]+(?:\s+[A-Z][A-Za-z\'’.-]+)+', candidate_clean):
                        author_names.append(candidate_clean)
                    elif len(candidate_clean.split()) <= 6 and re.fullmatch(r'[A-Z][A-Za-z\'’.-]+(?:\s+[A-Z]\.)?\s+[A-Z][A-Za-z\'’.-]+', candidate_clean):
                        author_names.append(candidate_clean)

        # Also scan for comma-separated name groups on a single line after a by-line.
        for index, line in enumerate(lines[:80]):
            if index < skip_until_line:
                continue
            if re.search(r'(?i)\b(?:message from|chairperson|chairman|director general|governor|deputy governor)\b', line):
                skip_until_line = min(len(lines), index + 2)
                continue
            lower = line.lower()
            if lower.strip() in {'working paper series', 'research paper series'}:
                continue
            if any(lower.startswith(f"{label}:") or lower == label for label in labels):
                continue
            if any(token in lower for token in ('department', 'directorate', 'division', 'team', 'unit', 'ministry', 'bank')):
                continue
            if any(name in lower for name in ('prepared by', 'written by', 'study by')):
                continue
            if len(line.split()) <= 6 and re.fullmatch(r'[A-Z][A-Za-z\'’.-]+(?:\s+[A-Z][A-Za-z\'’.-]+)+', line) and not re.search(r'\b(?:department|directorate|division|team|unit|ministry|bank)\b', line, re.IGNORECASE):
                author_names.append(line.strip().strip(',:;'))

        seen = set()
        cleaned = []
        for name in author_names:
            if len(name.split()) > 4:
                split_names = re.findall(r"[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+", name)
                if len(split_names) > 1:
                    author_names.extend(split_names)
                    continue
            norm = re.sub(r'\s+', ' ', name).strip()
            if not norm or len(norm) < 4 or norm.isupper():
                continue
            if norm.lower() in seen:
                continue
            seen.add(norm.lower())
            cleaned.append(norm)
        return cleaned
    
    def validate_file(self, filename: str, file_size: int, content_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate file type and size
        Returns: (is_valid, error_message)
        """
        # Check file size
        if file_size > self.MAX_FILE_SIZE:
            return False, "File size exceeds the maximum allowed limit of 50 MB."
        
        # Check file extension
        file_extension = os.path.splitext(filename or '')[1].lstrip('.').lower()
        if file_extension not in self.ALLOWED_TYPES:
            return False, f"Unsupported file type: {file_extension}. Please upload PDF or DOCX."

        expected_type = self.ALLOWED_TYPES[file_extension]
        if content_type and content_type != expected_type:
            return False, "The uploaded file type does not match its filename extension."
        
        return True, ""
    
    def extract_from_pdf(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from PDF using PyPDF2 and pdfplumber
        """
        logger.info(f"Extracting text from PDF: {file_path}")
        
        # Initialize extraction
        extracted_data = {
            'text': '',
            'pages': [],
            'metadata': {'pages': 0}
        }
        
        try:
            # Try PyPDF2 first
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                extracted_data['metadata']['pages'] = len(pdf_reader.pages)
                pdf_metadata = pdf_reader.metadata or {}
                extracted_data['metadata'].update({
                    'title': pdf_metadata.get('/Title'),
                    'author': pdf_metadata.get('/Author'),
                    'subject': pdf_metadata.get('/Subject'),
                })
                
                # Extract text page by page
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text() or ''
                    extracted_data['pages'].append({
                        'page_num': page_num,
                        'text': page_text
                    })
                    extracted_data['text'] += page_text + '\n'
            
            # If PyPDF2 extracted too little text, try pdfplumber (better for tables)
            if len(extracted_data['text']) < 100:
                logger.info("PyPDF2 extraction limited, trying pdfplumber...")
                text_from_plumber = self._extract_with_pdfplumber(file_path)
                if text_from_plumber and len(text_from_plumber) > len(extracted_data['text']):
                    extracted_data['text'] = text_from_plumber
            
            logger.info(f"Extracted {len(extracted_data['text'])} characters from PDF")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            raise
    
    def _extract_with_pdfplumber(self, file_path: str) -> str:
        """
        Extract text using pdfplumber (better for structured/tabular data)
        """
        try:
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n"
            return full_text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return ""
    
    def extract_from_docx(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from DOCX file
        """
        logger.info(f"Extracting text from DOCX: {file_path}")
        
        extracted_data = {
            'text': '',
            'pages': [],
            'metadata': {'pages': 1}  # DOCX doesn't have pages
        }
        
        try:
            doc = DocxDocument(file_path)
            full_text = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        full_text.append(' | '.join(row_text))
            
            extracted_data['text'] = '\n'.join(full_text)
            core_properties = doc.core_properties
            extracted_data['metadata'].update({
                'title': core_properties.title,
                'author': core_properties.author,
                'subject': core_properties.subject,
                'created': core_properties.created,
            })
            logger.info(f"Extracted {len(extracted_data['text'])} characters from DOCX")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting from DOCX: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        # Keep line boundaries because they carry title-page and metadata signals.
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'[\t\f\v ]+', ' ', text)
        text = re.sub(r'[^\w\s.,;:!?()\[\]{}%&/+\-]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = None,
        overlap: int = None,
        page_data: Optional[List[Dict[str, any]]] = None,
    ) -> List[Dict[str, any]]:
        """
        Split text into overlapping chunks
        """
        if not text:
            return []
        
        chunk_size = chunk_size or self.CHUNK_SIZE
        overlap = overlap or self.CHUNK_OVERLAP
        
        chunks = []

        if page_data:
            for page in page_data:
                page_chunks = self.chunk_text(page.get('text', ''), chunk_size, overlap)
                for page_chunk in page_chunks:
                    page_chunk['page_number'] = page.get('page_num')
                    page_chunk['index'] = len(chunks)
                    chunks.append(page_chunk)
            logger.info(f"Created {len(chunks)} page-aware chunks from text")
            return chunks
        
        # Split into sentences first (better for semantic meaning)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            # If adding this sentence exceeds chunk size, save current chunk
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append({
                    'index': chunk_index,
                    'text': current_chunk.strip(),
                    'length': len(current_chunk.strip())
                })
                chunk_index += 1
                
                # Keep overlap for context
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add last chunk if exists
        if current_chunk.strip():
            chunks.append({
                'index': chunk_index,
                'text': current_chunk.strip(),
                'length': len(current_chunk.strip())
            })
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def process_document(self, file_path: str, filename: str, document_id: int) -> Dict[str, any]:
        """
        Main method to process a document
        """
        logger.info(f"Processing document: {filename} (ID: {document_id})")
        
        # Determine file type
        file_extension = filename.split('.')[-1].lower()
        
        # Extract text
        if file_extension == 'pdf':
            extracted = self.extract_from_pdf(file_path)
        elif file_extension == 'docx':
            extracted = self.extract_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Clean text
        cleaned_text = self.clean_text(extracted['text'])
        # The cover page is the strongest source for publication metadata. Use the
        # rest of the document only when the cover does not provide a value.
        cover_text = extracted['pages'][0]['text'] if extracted.get('pages') else extracted['text']
        cover_metadata = self.extract_content_metadata(
            cover_text,
            filename,
            include_institutional_fallback=False,
        )
        content_metadata = self.extract_content_metadata(extracted['text'], filename)
        native_author = self.clean_title_text(extracted['metadata'].get('author'))
        native_author_lower = (native_author or '').lower()
        native_author_is_institution = native_author_lower in {'bank of tanzania', 'government of tanzania'}
        native_author_is_valid = bool(
            native_author
            and (native_author_is_institution or 2 <= len(native_author.split()) <= 6)
            and not re.search(r'\d|@|https?://', native_author)
            and (native_author_is_institution or not any(label in native_author_lower for label in self.NON_AUTHOR_LABELS))
        )
        cover_institution_evidence = bool(re.search(
            r'(?i)\b(?:bank of tanzania|government of tanzania|conference|proceedings|financial stability report|framework)\b',
            cover_text,
        ))
        if cover_metadata.get('author'):
            for key in ('author', 'authors', 'author_type', 'author_confidence', 'author_source'):
                if cover_metadata.get(key):
                    content_metadata[key] = cover_metadata[key]
            content_metadata['author_source'] = f"cover page: {cover_metadata.get('author_source') or 'explicit metadata'}"
        elif cover_institution_evidence:
            content_metadata['authors'] = ['Bank of Tanzania']
            content_metadata['author'] = 'Bank of Tanzania'
            content_metadata['author_type'] = 'institutional'
            content_metadata['author_confidence'] = 0.98
            content_metadata['author_source'] = 'cover page institutional attribution'
        elif native_author_is_valid:
            content_metadata.update({
                'authors': [native_author],
                'author': native_author,
                'author_type': 'institutional' if native_author_is_institution else 'individual',
                'author_confidence': 0.96,
                'author_source': 'embedded document metadata',
            })
        for key in ('publication_year', 'publication_year_confidence', 'publication_year_source', 'publication_period'):
            if cover_metadata.get(key):
                content_metadata[key] = cover_metadata[key]
        native_title = self.clean_title_text(extracted['metadata'].get('title'))
        native_title_is_placeholder = bool(
            native_title
            and (
                native_title.lower() in {'untitled', 'document', 'file', 'microsoft word', 'pdf'}
                or re.match(r'(?i)^(?:microsoft word|adobe acrobat|chrome|scan)', native_title)
                or native_title.lower() == (self.clean_title_text(filename) or '').lower()
            )
        )
        if native_title and not native_title_is_placeholder and native_title.lower() not in {'bank of tanzania', 'the bank of tanzania', 'government of tanzania'}:
            content_metadata['title'] = native_title
        if extracted['metadata'].get('author') and any(label in str(extracted['metadata']['author']).lower() for label in self.NON_AUTHOR_LABELS):
            extracted['metadata']['author'] = None
        for key, value in content_metadata.items():
            if not extracted['metadata'].get(key) or (key == 'title' and str(extracted['metadata'].get(key)).strip().lower() in {'bank of tanzania', 'the bank of tanzania', 'government of tanzania'}):
                extracted['metadata'][key] = value
        # Publication authors must come from explicit document text, never from
        # embedded PDF metadata such as the file creator.
        extracted['metadata']['author'] = content_metadata.get('author')
        if str(extracted['metadata'].get('document_type', '')).strip().lower() in {'form', 'document', 'publication'} and content_metadata.get('document_type'):
            extracted['metadata']['document_type'] = content_metadata['document_type']
        
        # Create chunks
        chunks = self.chunk_text(cleaned_text, page_data=extracted.get('pages'))
        
        # Prepare result
        result = {
            'document_id': document_id,
            'file_name': filename,
            'file_type': file_extension,
            'total_pages': extracted['metadata'].get('pages', 1),
            'total_chunks': len(chunks),
            'total_characters': len(cleaned_text),
            'cleaned_text': cleaned_text,
            'chunks': chunks,
            'page_data': extracted.get('pages', []),
            'metadata': extracted.get('metadata', {})
        }
        
        logger.info(f"Document processing complete: {filename} ({len(cleaned_text)} chars, {len(chunks)} chunks)")
        return result

    def extract_content_metadata(
        self,
        text: str,
        filename: str,
        include_institutional_fallback: bool = True,
    ) -> Dict[str, any]:
        """Extract metadata using document structure and explicit evidence only."""
        metadata = {}
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        normalized_filename = self.clean_title_text(filename) or ""
        filename_lower = filename.lower()
        filename_title_words = {
            word.lower()
            for word in re.findall(r"[A-Za-z]+", normalized_filename)
            if len(word) > 2 and word.lower() not in {"working", "papers", "series"}
        }

        def bounded(value: Optional[str], limit: int) -> Optional[str]:
            if value is None:
                return None
            cleaned = self.clean_title_text(str(value))
            return cleaned[:limit].rstrip(' ,.;:-') if cleaned else None

        def labelled_value(labels):
            pattern = r"^\s*(?:" + "|".join(labels) + r")\s*[:\-]\s*(.+?)\s*$"
            for line in lines[:80]:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip().rstrip('.,;')
            return None

        def normalize_author_names(values: List[str]) -> List[str]:
            cleaned: List[str] = []
            seen = set()
            generic_document_labels = (
                'research report', 'working paper', 'policy brief', 'annual report', 'quarterly economic bulletin',
                'monthly economic review', 'strategic plan', 'financial stability report', 'framework', 'statement',
                'notice', 'calendar', 'report', 'paper', 'bulletin', 'brief', 'review', 'study', 'document'
            )
            for value in values:
                if value is None:
                    continue
                author = bounded(value, 255)
                if not author:
                    continue
                lower_author = author.lower()
                if lower_author in generic_document_labels or any(key in lower_author for key in ('research report', 'working paper', 'annual report', 'quarterly economic bulletin', 'monthly economic review', 'financial stability report', 'policy brief', 'framework', 'public notice', 'issuance calendar', 'statement', 'brief', 'bulletin', 'review', 'study', 'report')):
                    continue
                if re.search(r'\d', author):
                    continue
                if any(token in lower_author for token in ('department', 'directorate', 'division', 'team', 'unit', 'ministry', 'bank', 'institution', 'institute', 'committee')):
                    continue
                if any(label in lower_author for label in self.NON_AUTHOR_LABELS):
                    continue
                if len(author.split()) > 6:
                    continue
                if len(author.split()) < 2:
                    continue
                author_words = {word.lower() for word in re.findall(r"[A-Za-z]+", author) if len(word) > 2}
                if author_words and author_words.issubset(filename_title_words):
                    continue
                norm = re.sub(r'\s+', ' ', author).strip(' ,;:')
                if not norm or norm.isupper():
                    continue
                key = norm.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(norm)
            return cleaned

        explicit_title = labelled_value(['title'])
        explicit_author = labelled_value(['author', 'authors', 'by', 'prepared by', 'written by', 'researcher', 'researchers', 'research team', 'research conducted by', 'prepared and compiled by', 'contributors'])
        if explicit_author and (
            len(explicit_author.split()) > 30
            or re.search(r'\b(i am|we are|present|report|street|dar es salaam|highlights)\b', explicit_author, re.IGNORECASE)
        ):
            explicit_author = None
        candidate_authors = self.extract_author_candidates(text)
        has_author_marker = any(
            re.match(
                r'^\s*(?:author|authors|by|prepared by|written by|researcher|researchers|research team|research conducted by|prepared and compiled by|contributors)\s*:?\s*$',
                line,
                re.IGNORECASE,
            )
            for line in lines[:80]
        )
        is_working_paper = bool(re.search(r'(?i)working paper|wp no|research paper', filename + ' ' + text[:2500]))
        is_institutional_publication = bool(re.search(
            r'(?i)research newsletter|bot newsletter|monetary policy statement|financial stability report|annual report|economic review|economic bulletin|zonal economic report|weekly financial markets report|conference|proceedings|framework|institutional report',
            filename + ' ' + text[:2500],
        ))
        author_values = []
        if explicit_author:
            explicit_parts = re.split(r'\s*,\s*|\s+and\s+|\s*&\s*|\s*;\s*', explicit_author, flags=re.IGNORECASE)
            author_values = [part.strip() for part in explicit_parts if part and part.strip()]
        candidate_values = candidate_authors if ((has_author_marker or is_working_paper) and not is_institutional_publication) else []
        metadata['authors'] = normalize_author_names(author_values + candidate_values)
        metadata['author'] = ', '.join(metadata['authors']) if metadata['authors'] else None
        metadata['author_type'] = 'individual' if metadata['authors'] else 'unknown'
        metadata['author_confidence'] = 0.94 if metadata['authors'] else 0.0
        metadata['author_source'] = 'explicit author label' if metadata['authors'] else None
        if not metadata['authors'] and candidate_authors and is_working_paper and not is_institutional_publication:
            metadata['authors'] = normalize_author_names(candidate_authors)
            metadata['author'] = ', '.join(metadata['authors'])
            metadata['author_type'] = 'individual'
            metadata['author_confidence'] = 0.94
            metadata['author_source'] = 'working paper cover author line'
        if metadata.get('author') and all(label in metadata['author'].lower() for label in ('research department', 'department')):
            metadata['author'] = None
        if metadata.get('author') and any(label in metadata['author'].lower() for label in self.NON_AUTHOR_LABELS):
            metadata['author'] = None
            metadata['authors'] = []
            metadata['author_type'] = 'unknown'
            metadata['author_confidence'] = 0.0
            metadata['author_source'] = None

        institution_evidence = re.search(r'(?i)\b(?:bank of tanzania|banktanzania)\b', text[:5000])
        bot_publication_evidence = re.search(
            r'(?i)\b(?:bank of tanzania|research newsletter|research bulletin|monetary policy|statistical bulletin|annual report|strategic plan|monthly economic review|quarterly economic bulletin|conference|proceedings|framework|institutional report)\b',
            text[:8000],
        ) or re.search(r'(?i)\b(?:bank of tanzania|bot)\b', filename)
        if include_institutional_fallback and not metadata['authors'] and institution_evidence and bot_publication_evidence and not is_institutional_publication:
            metadata['authors'] = ['Bank of Tanzania']
            metadata['author'] = 'Bank of Tanzania'
            metadata['author_type'] = 'institutional'
            metadata['author_confidence'] = 0.98
            metadata['author_source'] = 'publication institutional attribution'
        elif include_institutional_fallback and not metadata['authors'] and bot_publication_evidence:
            metadata['authors'] = ['Bank of Tanzania']
            metadata['author'] = 'Bank of Tanzania'
            metadata['author_type'] = 'institutional'
            metadata['author_confidence'] = 0.9
            metadata['author_source'] = 'BOT publication classification'
        metadata['department'] = labelled_value(['department', 'unit', 'directorate', 'division'])
        metadata['document_type'] = labelled_value(['document type', 'publication type', 'type'])
        if not metadata['document_type']:
            metadata['document_type'] = next((name for name, evidence in self.DOCUMENT_TYPE_RULES.items() if any(term in filename_lower for term in evidence)), None)
        topic_value = labelled_value(['research topics', 'topics', 'subject', 'subjects'])
        if topic_value:
            metadata['topics'] = [item.strip() for item in re.split(r'[,;|]', topic_value) if item.strip()]
        keyword_value = labelled_value(['keywords', 'key words'])
        if keyword_value:
            metadata['keywords'] = [item.strip().lower() for item in re.split(r'[,;|]', keyword_value) if item.strip()]

        text_lower = text.lower()
        if not metadata.get('topics'):
            metadata['topics'] = [
                topic for topic, evidence in self.TOPIC_RULES.items()
                if any(term in text_lower for term in evidence)
            ]

        filename_category = next(
            (name for name, evidence in self.CATEGORY_RULES.items() if any(term in filename_lower for term in evidence)),
            None,
        )
        category_scores = {
            name: sum(text_lower.count(term) + filename_lower.count(term) * 3 for term in evidence)
            for name, evidence in self.CATEGORY_RULES.items()
        }
        metadata['category'] = filename_category or (max(category_scores, key=category_scores.get) if max(category_scores.values(), default=0) else None)

        title_candidates = []
        generic_title_tokens = (
            'research report', 'working paper', 'policy brief', 'annual report', 'quarterly economic bulletin',
            'monthly economic review', 'financial stability report', 'statistical bulletin', 'strategic plan',
            'public notice', 'research newsletter', 'newsletter', 'framework', 'statement', 'report', 'paper',
            'bulletin', 'brief', 'review', 'study', 'journal'
        )
        explicit_title_value = self.clean_title_text(explicit_title) if explicit_title else None
        if explicit_title_value:
            metadata['title'] = bounded(explicit_title_value, 500)
        else:
            for index, line in enumerate(lines[:25]):
                normalized = self.clean_title_text(line)
                if not normalized:
                    continue
                if len(normalized) < 8 or len(normalized) > 220:
                    continue
                lowered = normalized.lower()
                if normalized.lower() in {'bank of tanzania', 'the bank of tanzania', 'government of tanzania', 'bank', 'tanzania'}:
                    continue
                if len(re.findall(r'\b[A-Z]{2,5}\b', normalized)) >= 4:
                    continue
                if re.match(r'(?i)^(?:issn|isbn|doi|wp\s*no)\b', normalized):
                    continue
                if re.match(r'^(?:message from|chairperson|chairman|chairwoman|director general|governor|deputy governor|welcome remarks|opening remarks)\b', normalized, re.IGNORECASE):
                    continue
                if index > 0 and re.match(r'^(?:message from|chairperson|chairman|chairwoman|director general|governor|deputy governor|welcome remarks|opening remarks)\b', lines[index - 1], re.IGNORECASE):
                    continue
                if re.match(r'^(author|authors|by|prepared by|written by|published|publication|keywords?|topics?|subjects?|department|unit|type|research team|study by)\s*[:\-]', normalized, re.IGNORECASE):
                    continue
                if re.fullmatch(r'(?:[A-Z][a-z]+|[A-Z]\.)+(?:\s+(?:[A-Z][a-z]+|[A-Z]\.))*', normalized) and len(normalized.split()) <= 6:
                    continue
                if re.fullmatch(r'(?i)(?:financial stability|monetary policy|economic review|annual report|quarterly economic bulletin|monthly economic review|payment systems|government finance|research newsletter|public notice|policy brief|strategic plan|statistical bulletin|working paper|weekly financial markets report|zonal economic report|conference proceedings|framework|report|review|bulletin|brief|statement|calendar)\s*(?:framework|report|review|bulletin|brief|statement|calendar)?', normalized):
                    continue
                if re.search(r'\b[A-Z]\.|\b[A-Z][a-z]+,\s*[A-Z][a-z]+|\b(?:[A-Z][a-z]+\s+[A-Z]\.|[A-Z]\.[A-Z])', normalized):
                    if ',' in normalized or re.search(r'\b[A-Z]\.', normalized):
                        continue
                if any(token in lowered for token in generic_title_tokens):
                    if lowered in generic_title_tokens:
                        continue
                if any(token in normalized.lower() for token in ('department:', 'unit:', 'directorate:', 'division:', 'research department', 'prepared by', 'written by')):
                    continue
                title_candidates.append(normalized)

            filename_title = self.clean_title_text(normalized_filename)
            filename_title = re.sub(r'\bTanzania\s+(?=Exports\b)', "Tanzania's ", filename_title) if filename_title else None
            if filename_title:
                prefix_match = re.match(r'^(?P<prefix>[A-Za-z][A-Za-z &/]+?)\s*[-–—]\s*(?P<title>.+)$', filename_title)
                if prefix_match:
                    prefix = prefix_match.group('prefix').strip().lower()
                    if prefix in {'financial stability', 'research newsletter', 'public notice', 'payment systems', 'monetary policy', 'economic review', 'annual report', 'annual reports', 'policy brief', 'strategic plan', 'working paper', 'tanzania investment'}:
                        filename_title = prefix_match.group('title').strip()
            filename_is_generic = bool(
                filename_title
                and (
                    re.fullmatch(r'(?:document|file|scan|upload|report)[\s_-]*(?:\d+)?', filename_title, re.IGNORECASE)
                    or filename_title.lower() in generic_title_tokens
                )
            )
            if not metadata.get('title'):
                if filename_title and len(filename_title.split()) >= 2 and not filename_is_generic:
                    metadata['title'] = bounded(filename_title, 500)
                elif title_candidates:
                    preferred = sorted(title_candidates, key=lambda item: (len(item.split()), item.count(' ')), reverse=True)
                    metadata['title'] = bounded(preferred[0], 500)
                elif filename_title:
                    metadata['title'] = bounded(filename_title, 500)

        if metadata.get('title'):
            metadata['title'] = self.clean_title_text(metadata['title'])
            metadata['title'] = re.sub(r'\s+((?:19|20)\d{2})$', '', metadata['title']) if metadata['title'] else None
            metadata['title'] = self.clean_title_text(metadata['title']) if metadata['title'] else None
            if metadata['title'] and not re.search(r'[A-Za-z]', metadata['title']):
                metadata['title'] = None

        period_source = text[:6000] + ' ' + filename
        period_match = re.search(r'\b((?:19|20)\d{2})\s*/\s*\d{2,4}\s*(?:-|–|—|to)\s*((?:19|20)\d{2})\s*/\s*(\d{2,4})\b', period_source, re.IGNORECASE)
        if period_match:
            end_year = period_match.group(3)
            if len(end_year) == 2:
                end_year = f'{period_match.group(2)[:2]}{end_year}'
            metadata['publication_period'] = f'{period_match.group(1)}-{end_year}'
            metadata['publication_year'] = int(period_match.group(1))
            metadata['publication_year_source'] = 'explicit publication period'
            metadata['publication_year_confidence'] = 0.99
        else:
            period_match = re.search(r'\b((?:19|20)\d{2})\s*(?:-|–|—|to|/)\s*((?:19|20)\d{2})\b', period_source, re.IGNORECASE)
            if period_match:
                metadata['publication_period'] = f'{period_match.group(1)}-{period_match.group(2)}'
                metadata['publication_year'] = int(period_match.group(1))
                metadata['publication_year_source'] = 'explicit publication period'
                metadata['publication_year_confidence'] = 0.98
            else:
                explicit_year = re.search(
                    r'(?im)^\s*(?:publication year|publication date|published|issued|year|reporting period)\s*[:\-]?\s*((?:19|20)\d{2})\b',
                    '\n'.join(lines[:80]),
                )
                filename_year = re.search(r'\b(?:19|20)\d{2}\b', filename)
                cover_year = None
                for cover_line in lines[:25]:
                    if not re.search(r'(?i)published|publication|issued|reporting period|wp\s*no|working paper|(?:january|february|march|april|may|june|july|august|september|october|november|december)', cover_line):
                        continue
                    cover_year = re.search(r'\b(?:19|20)\d{2}\b', cover_line)
                    if cover_year:
                        break
                month_years = re.findall(
                    r'(?i)(?:january|february|march|april|may|june|july|august|september|october|november|december)\s*((?:19|20)\d{2})',
                    '\n'.join(lines[:25]),
                )
                if explicit_year:
                    metadata['publication_year'] = int(explicit_year.group(1))
                    metadata['publication_year_source'] = 'explicit publication year label'
                    metadata['publication_year_confidence'] = 0.99
                elif len(month_years) >= 2 and len(set(month_years)) == 2:
                    metadata['publication_period'] = f'{month_years[0]}-{month_years[-1]}'
                    metadata['publication_year'] = int(month_years[-1])
                    metadata['publication_year_source'] = 'cover page publication period'
                    metadata['publication_year_confidence'] = 0.97
                elif filename_year:
                    metadata['publication_year'] = int(filename_year.group(0))
                    metadata['publication_year_source'] = 'filename year'
                    metadata['publication_year_confidence'] = 0.93
                elif cover_year:
                    metadata['publication_year'] = int(cover_year.group(0))
                    metadata['publication_year_source'] = 'cover page publication year'
                    metadata['publication_year_confidence'] = 0.94

        metadata['metadata_review_status'] = (
            'reviewed'
            if metadata.get('author_confidence', 0) >= 0.9
            and metadata.get('publication_year_confidence', 0) >= 0.9
            else 'needs_review'
        )
        return {key: value for key, value in metadata.items() if value is not None and value != []}