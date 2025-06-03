# RAG (Retrieval-Augmented Generation) Feature

This implementation provides a complete RAG system for your Python FastAPI application, equivalent to the C# PostgresDatabase class you provided.

## Features

- 📄 **Document Processing**: Support for PDF, DOCX, TXT, and code files
- 🔢 **Vector Storage**: PostgreSQL with pgvector extension for efficient vector storage
- 🔍 **Similarity Search**: Cosine similarity search using OpenAI embeddings
- 📊 **Chunking**: Intelligent text chunking with configurable overlap
- 🔌 **API Endpoints**: Ready-to-use FastAPI endpoints

## Quick Start

### 1. Setup Environment

Make sure you have the required environment variables:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost/dbname"
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. Install Dependencies

```bash
pip install PyPDF2==3.0.1 python-docx==1.1.0
```

### 3. Run Database Setup

```bash
# Initialize RAG database setup
curl -X POST "http://localhost:8000/api/v1/rag/setup"
```

## API Endpoints

### Upload and Process Files

```bash
# Upload a file and automatically vectorize it
curl -X POST "http://localhost:8000/api/v1/rag/upload-file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Insert Text Directly

```python
import requests

data = {
    "file_path": "manual_input.txt",
    "snippets": [
        "This is the first text chunk to vectorize.",
        "This is the second text chunk with different content."
    ]
}

response = requests.post(
    "http://localhost:8000/api/v1/rag/insert-text",
    json=data
)
```

### Search Similar Content

```bash
# Search using GET
curl "http://localhost:8000/api/v1/rag/search/What%20is%20Python?limit=5&min_similarity=0.3"

# Search using POST
curl -X POST "http://localhost:8000/api/v1/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python?",
    "limit": 5,
    "min_similarity": 0.3
  }'
```

### List Files and Vectors

```bash
# List all source files
curl "http://localhost:8000/api/v1/rag/files"

# List all vectors (debugging)
curl "http://localhost:8000/api/v1/rag/vectors"
```

### Get Document by ID

```bash
# Get a specific document by vector ID
curl "http://localhost:8000/api/v1/rag/document/123"
```

### Delete Files

```bash
# Delete a source file and all its vectors
curl -X DELETE "http://localhost:8000/api/v1/rag/file/document.pdf"
```

## Python Usage Examples

### Basic RAG Operations

```python
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentProcessor
from app.models.rag import DocumentRecord
from app.database import async_session

async def example_usage():
    rag_service = RAGService()
    doc_processor = DocumentProcessor()

    async with async_session() as db:
        # Setup database
        await rag_service.ensure_database_setup(db)

        # Process and store a document
        file_content = b"Your document content here..."
        chunks = doc_processor.process_file(file_content, "example.txt")

        await rag_service.insert_document_with_chunks(
            db=db,
            file_path="example.txt",
            text_chunks=chunks
        )

        # Search for similar content
        results = await rag_service.search_similar_vectors(
            db=db,
            query_text="search query",
            limit=5
        )

        for result in results:
            print(f"Similarity: {result.similarity}")
            print(f"File: {result.file_path}")
            print(f"Content: {result.snippet}")
```

### Document Processing

```python
from app.services.document_processor import DocumentProcessor

doc_processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)

# Process different file types
pdf_chunks = doc_processor.process_file(pdf_bytes, "document.pdf")
docx_chunks = doc_processor.process_file(docx_bytes, "document.docx")
txt_chunks = doc_processor.process_file(txt_bytes, "document.txt")

# Manual text chunking
text = "Your long text here..."
chunks = doc_processor.chunk_text(text)
```

## Configuration

### Document Processor Settings

- `chunk_size`: Number of words per chunk (default: 1000)
- `chunk_overlap`: Number of overlapping words between chunks (default: 200)

### Supported File Types

- **PDF**: `.pdf`
- **Word Documents**: `.docx`, `.doc`
- **Text Files**: `.txt`, `.md`
- **Code Files**: `.py`, `.js`, `.html`, `.css`, `.json`, `.xml`

## Database Schema

### Source Files Table

```sql
CREATE TABLE source_files (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Vectors Table

```sql
CREATE TABLE vectors (
    id SERIAL PRIMARY KEY,
    source_file_id INTEGER REFERENCES source_files(id) ON DELETE CASCADE,
    vector_data vector(1536) NOT NULL,
    snippet TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Testing

Run the test script to verify functionality:

```bash
python test_rag.py
```

## Equivalent C# Methods

This Python implementation provides the following equivalents to your C# PostgresDatabase class:

- `EnsureTableExistsAsync()` → `ensure_database_setup()`
- `InsertPdfRecordAsync()` → `insert_document_record()`
- `SearchSimilarVectorsAsync()` → `search_similar_vectors()`
- `GetPdfRecordByIdAsync()` → `get_document_record_by_id()`
- `PrintSourceFilesAsync()` → `get_all_source_files()`
- `PrintVectorsAsync()` → `get_all_vectors()`

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid file type or empty content
- **404 Not Found**: Document not found
- **500 Internal Server Error**: Database or processing errors

## Performance Notes

- Uses pgvector's efficient cosine similarity operator (`<=>`)
- Implements connection pooling with async SQLAlchemy
- Supports batch operations for multiple documents
- Configurable similarity thresholds for filtering results
