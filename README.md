# Education Platform API

A FastAPI-based education platform with PostgreSQL database, pgvector for semantic search, and Azure OpenAI integration.

## Features

- 🚀 **FastAPI** with async support
- 🐘 **PostgreSQL** with **pgvector** for vector similarity search
- 🔍 **RAG (Retrieval-Augmented Generation)** for context-aware AI responses
- 📁 **File attachments** with vector embeddings
- 💬 **Chat system** with message history
- 🏢 **Multi-workspace** support
- 🗃️ **Database migrations** with Alembic
- 🔐 **Azure OpenAI** integration

## Database Schema

### Tables

- **workspaces**: Organization/project containers
- **chats**: Conversations within workspaces
- **messages**: Chat messages with role (user/assistant)
- **attachments**: Files with vector embeddings for similarity search

### Vector Search

- Uses **pgvector** extension for efficient similarity search
- **1536-dimensional** vectors (OpenAI embedding size)
- **Cosine similarity** with IVFFlat index for performance

## Setup

### 1. Environment Setup

```bash
# Clone and setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Database (replace with your Azure PostgreSQL details)
DATABASE_URL=postgresql+asyncpg://username:password@host:5432/database?sslmode=require

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Alternative: Direct OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### 3. Database Setup

#### Option A: Azure PostgreSQL with pgvector

1. Create Azure Database for PostgreSQL Flexible Server
2. Enable pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Update connection string in both `app/config.py` and `alembic.ini`

#### Option B: Local PostgreSQL

```bash
# Install PostgreSQL and pgvector extension
# Then create database
createdb eduplatform
```

### 4. Run Migrations

```bash
# Apply database migrations
alembic upgrade head
```

### 5. Start Application

```bash
# Development
uvicorn app.main:app --reload

# Production
python startup.py
```

## API Usage

### Core Endpoints

#### Workspaces

```bash
# Create workspace
POST /api/v1/workspaces/
{
  "name": "My Project"
}

# List workspaces
GET /api/v1/workspaces/
```

#### Chats

```bash
# Create chat
POST /api/v1/chats/
{
  "name": "AI Discussion",
  "workspace_id": "workspace-uuid"
}

# Get chat messages
GET /api/v1/chats/{chat_id}/messages
```

#### Attachments with Vector Search

```bash
# Upload attachment with embedding
POST /api/v1/attachments/
{
  "name": "document.pdf",
  "type": "pdf",
  "azure_blob_path": "/path/to/blob",
  "workspace_id": "workspace-uuid",
  "content_vector": [0.1, 0.2, ...] // 1536-dim embedding
}

# Search similar content
POST /api/v1/attachments/search
{
  "query_vector": [0.1, 0.2, ...],
  "workspace_id": "workspace-uuid",
  "limit": 10,
  "similarity_threshold": 0.7
}
```

### Service Layer Example

```python
from app.services.chat_service import ChatService
from app.database import get_db

async def example_usage():
    async with get_db() as db:
        service = ChatService(db)

        # Create chat with RAG-enabled AI response
        chat, user_msg = await service.create_chat_with_context(
            workspace_id="workspace-uuid",
            name="AI Chat",
            initial_message="Tell me about machine learning"
        )

        # Add message with AI response using vector search
        user_msg, ai_msg = await service.add_message_with_ai_response(
            chat_id=chat.id,
            user_message="What are neural networks?",
            use_rag=True  # Will search attachments for context
        )
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Service Layer  │    │  Repository     │
│   Routes        │───▶│   Business Logic │───▶│  Database ORM   │
│                 │    │   + AI Logic     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pydantic      │    │   OpenAI API     │    │  PostgreSQL     │
│   Models        │    │   Embeddings     │    │  + pgvector     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Vector Search Process

1. **Document Upload**: Generate embeddings using OpenAI's `text-embedding-ada-002`
2. **Storage**: Store 1536-dimensional vectors in PostgreSQL with pgvector
3. **Query**: Convert user queries to embeddings
4. **Search**: Use cosine similarity to find relevant documents
5. **RAG**: Include relevant context in AI prompts

## Database Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

## Deployment

### Azure App Service

1. Set environment variables in App Service configuration
2. Ensure Azure PostgreSQL firewall allows App Service IPs
3. Use provided `startup.py` for production

### Docker (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "startup.py"]
```

## Development

### Adding New Models

1. Update SQLAlchemy models in `app/models/db_models.py`
2. Update Pydantic models in `app/models/`
3. Create migration: `alembic revision --autogenerate -m "Add new model"`
4. Apply migration: `alembic upgrade head`

### Vector Search Performance

- **IVFFlat index** for faster similarity search
- Adjust `lists` parameter based on data size
- Consider **HNSW** index for very large datasets

## Security Notes

- Database passwords contain special characters - use URL encoding
- Enable SSL for Azure PostgreSQL connections
- Store API keys in environment variables or Azure Key Vault
- Use connection pooling for production workloads

## Troubleshooting

### Connection Issues

- Verify Azure PostgreSQL firewall settings
- Check SSL requirements (`sslmode=require`)
- URL-encode special characters in passwords

### Vector Extension

```sql
-- Verify pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Create if missing
CREATE EXTENSION IF NOT EXISTS vector;
```

### Performance

- Monitor vector search performance with query plans
- Adjust similarity thresholds based on use case
- Consider batch processing for large embedding operations
