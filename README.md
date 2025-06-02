# RAG Chatbot API

A production-ready RAG (Retrieval-Augmented Generation) chatbot API built with FastAPI, PostgreSQL with pgvector, and Azure OpenAI. Designed for deployment on Azure App Service.

## Features

- **RAG Chatbot**: Context-aware responses using document embeddings
- **Vector Search**: PostgreSQL with pgvector for semantic document search
- **Azure OpenAI Integration**: GPT models and embeddings
- **Document Management**: Upload and manage knowledge base documents
- **Chat Sessions**: Persistent conversation history
- **Streaming Responses**: Real-time chat experience
- **Azure App Service Ready**: Production deployment configuration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │◄──►│   PostgreSQL     │    │   Azure OpenAI  │
│                 │    │   + pgvector     │◄──►│                 │
│   - Chat API    │    │                  │    │  - GPT Models   │
│   - Document    │    │  - Documents     │    │  - Embeddings   │
│     Management  │    │  - Embeddings    │    │                 │
│   - Vector      │    │  - Chat History  │    │                 │
│     Search      │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Local Development Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 13+ with pgvector extension
- Azure OpenAI resource with deployed models

### Installation

1. **Clone and setup environment**:

```bash
git clone <repository-url>
cd eduplatform-api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:

```bash
cp env.example .env
# Edit .env with your configuration
```

3. **Setup PostgreSQL with pgvector**:

```sql
-- Connect to your PostgreSQL instance
CREATE DATABASE ragchatbot;
\c ragchatbot;
CREATE EXTENSION vector;
```

4. **Run the application**:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

Copy `env.example` to `.env` and configure:

### Required Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://username:password@hostname:5432/database_name

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

## API Endpoints

### Documents

- `POST /api/v1/documents/` - Create document
- `POST /api/v1/documents/upload` - Upload file
- `GET /api/v1/documents/` - List documents
- `GET /api/v1/documents/{id}` - Get document
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/search` - Search documents

### Chat

- `POST /api/v1/chat/sessions` - Create chat session
- `GET /api/v1/chat/sessions/{id}` - Get session
- `GET /api/v1/chat/sessions?user_id=X` - List user sessions
- `POST /api/v1/chat/sessions/{id}/messages` - Send message
- `POST /api/v1/chat/sessions/{id}/stream` - Stream response

## Azure Deployment

### 1. Azure Resources Setup

**PostgreSQL with pgvector**:

```bash
# Create Azure Database for PostgreSQL Flexible Server
az postgres flexible-server create \
    --resource-group myResourceGroup \
    --name mypostgresql \
    --location eastus \
    --admin-user myadmin \
    --admin-password mypassword \
    --sku-name Standard_B1ms \
    --version 13
```

**Azure OpenAI**:

1. Create Azure OpenAI resource in Azure portal
2. Deploy models:
   - `gpt-35-turbo` for chat
   - `text-embedding-ada-002` for embeddings

### 2. Azure App Service Deployment

**Create App Service**:

```bash
az webapp create \
    --resource-group myResourceGroup \
    --plan myAppServicePlan \
    --name myragchatbot \
    --runtime "PYTHON|3.9"
```

**Configure App Settings**:

```bash
az webapp config appsettings set \
    --resource-group myResourceGroup \
    --name myragchatbot \
    --settings \
    DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
    AZURE_OPENAI_API_KEY="your-key" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-35-turbo" \
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-ada-002" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

**Deploy**:

```bash
# Option 1: Direct deployment
az webapp deployment source config-zip \
    --resource-group myResourceGroup \
    --name myragchatbot \
    --src deployment.zip

# Option 2: GitHub Actions (recommended)
# Set up GitHub Actions in your repository
```

### 3. Database Setup

Enable pgvector on your Azure PostgreSQL:

```sql
-- Connect to your Azure PostgreSQL instance
CREATE EXTENSION vector;
```

## Usage Examples

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Company Handbook",
       "content": "Welcome to our company...",
       "source": "handbook.pdf"
     }'
```

### Start a Chat Session

```bash
curl -X POST "http://localhost:8000/api/v1/chat/sessions" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user123",
       "title": "Help with policies"
     }'
```

### Send a Message

```bash
curl -X POST "http://localhost:8000/api/v1/chat/sessions/{session_id}/messages" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "What is the vacation policy?"
     }'
```

## Performance Considerations

- **Vector Search**: Uses cosine similarity with pgvector for fast retrieval
- **Connection Pooling**: Configured for optimal database connections
- **Async Operations**: Full async/await implementation for better concurrency
- **Chunking Strategy**: Smart text chunking with overlap for better context
- **Caching**: Redis support for caching frequent queries (optional)

## Monitoring

The application includes:

- Health check endpoints (`/health`)
- Structured logging
- Error handling and reporting
- Performance metrics ready for Azure Application Insights

## Security

- Environment-based configuration
- SQL injection protection via SQLAlchemy
- Input validation with Pydantic
- CORS configuration
- Rate limiting ready (can be added)

## Development

### Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application
├── config.py            # Configuration settings
├── database.py          # Database connection
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── api/
│   ├── documents.py     # Document endpoints
│   └── chat.py          # Chat endpoints
└── services/
    ├── azure_openai.py  # Azure OpenAI integration
    ├── document_service.py  # Document management
    └── chat_service.py  # Chat functionality
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## Troubleshooting

### Common Issues

1. **pgvector not found**: Ensure pgvector extension is installed and enabled
2. **Azure OpenAI errors**: Check endpoint URLs and API keys
3. **Database connection**: Verify connection string and network access
4. **Deployment issues**: Check Azure App Service logs

### Debugging

```bash
# Local debugging
export DEBUG=true
python -m uvicorn app.main:app --reload --log-level debug

# Check Azure logs
az webapp log tail --resource-group myResourceGroup --name myragchatbot
```

## License

MIT License - see LICENSE file for details.
