from typing import List
from pathlib import Path
import PyPDF2
import docx
from io import BytesIO

class DocumentProcessor:
    """Service for processing various document types and extracting text."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF bytes."""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX bytes."""
        try:
            doc = docx.Document(BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Error extracting text from DOCX: {str(e)}")
    
    def extract_text_from_txt(self, file_content: bytes) -> str:
        """Extract text from plain text bytes."""
        try:
            return file_content.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                return file_content.decode('latin-1').strip()
            except Exception as e:
                raise ValueError(f"Error extracting text from TXT: {str(e)}")
    
    def extract_text_from_file(self, file_content: bytes, file_extension: str) -> str:
        """Extract text from file based on extension."""
        file_extension = file_extension.lower().lstrip('.')
        
        if file_extension == 'pdf':
            return self.extract_text_from_pdf(file_content)
        elif file_extension in ['docx', 'doc']:
            return self.extract_text_from_docx(file_content)
        elif file_extension in ['txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml']:
            return self.extract_text_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []
        
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(words):
                break
        
        return chunks
    
    def process_file(self, file_content: bytes, file_name: str) -> List[str]:
        """Process a file and return text chunks."""
        file_extension = Path(file_name).suffix
        
        # Extract text
        text = self.extract_text_from_file(file_content, file_extension)
        
        # Split into chunks
        chunks = self.chunk_text(text)
        
        return chunks 