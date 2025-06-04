# RAG + Blob Storage Simplified Workflow

This document explains the simplified RAG (Retrieval-Augmented Generation) workflow that uses Azure Blob Storage directly without requiring an attachments table.

## Overview

The new workflow uses only the existing `source_files` and `vectors` tables, with blob paths stored as references. This eliminates the need for a separate attachments table while maintaining full RAG functionality.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │  Azure Blob     │
│                 │    │                 │    │   Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │  1. Request Upload    │                       │
         │     URL               │                       │
         ├──────────────────────▶│                       │
         │                       │                       │
         │  2. Return SAS URL    │                       │
         │     + blob_name       │                       │
         ◄──────────────────────┤                       │
         │                       │                       │
         │  3. Upload file       │                       │
         │     directly          │                       │
         ├───────────────────────┼──────────────────────▶│
         │                       │                       │
         │  4. Confirm upload    │                       │
         │     + process RAG     │                       │
         ├──────────────────────▶│                       │
         │                       │  5. Download & Process│
         │                       ├──────────────────────▶│
         │                       │                       │
         │  6. Return processed  │                       │
         │     document info     │                       │
         ◄──────────────────────┤                       │
```

## Workflow Steps

### 1. Generate Upload URL

```http
POST /api/v1/rag/workspaces/{workspace_id}/documents/upload-url
Content-Type: application/json

{
  "fileName": "document.pdf",
  "fileSize": 1024000,
  "mimeType": "application/pdf"
}
```

**Response:**

```json
{
  "uploadUrl": "https://storage.blob.core.windows.net/container/workspace/file?sas_token",
  "blobName": "workspace_id/20241201_123456_abc123_document.pdf",
  "containerName": "savedfiles",
  "expiryMinutes": 60
}
```

### 2. Upload File to Azure

```javascript
const response = await fetch(uploadInfo.uploadUrl, {
  method: "PUT",
  headers: {
    "x-ms-blob-type": "BlockBlob",
    "Content-Type": "application/pdf",
  },
  body: fileContent,
});
```

### 3. Confirm Upload and Process

```http
POST /api/v1/rag/workspaces/{workspace_id}/documents/confirm-upload
Content-Type: application/json

{
  "blobName": "workspace_id/20241201_123456_abc123_document.pdf",
  "fileName": "document.pdf",
  "replaceExisting": false
}
```

**Response:**

```json
{
  "id": "workspace_id/20241201_123456_abc123_document.pdf",
  "name": "document.pdf",
  "blobName": "workspace_id/20241201_123456_abc123_document.pdf",
  "workspace_id": "workspace_id",
  "chunks_count": 15,
  "status": "completed",
  "processed_at": "now",
  "url": "https://storage.blob.core.windows.net/container/workspace_id/file"
}
```

## API Endpoints

### Document Management

| Method | Endpoint                                           | Description              |
| ------ | -------------------------------------------------- | ------------------------ |
| POST   | `/workspaces/{id}/documents/upload-url`            | Generate upload URL      |
| POST   | `/workspaces/{id}/documents/confirm-upload`        | Confirm upload & process |
| GET    | `/workspaces/{id}/documents`                       | List workspace documents |
| DELETE | `/workspaces/{id}/documents/{doc_id}`              | Delete document          |
| GET    | `/workspaces/{id}/documents/{doc_id}/download-url` | Get download URL         |

### Search

| Method | Endpoint                  | Description                    |
| ------ | ------------------------- | ------------------------------ |
| POST   | `/workspaces/{id}/search` | Search within workspace        |
| POST   | `/search`                 | Global search (all workspaces) |

## Data Structure

### source_files table

```sql
CREATE TABLE source_files (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,  -- Contains blob path (workspace_id/timestamp_uuid_filename)
    created_at TIMESTAMP DEFAULT NOW()
);
```

### vectors table

```sql
CREATE TABLE vectors (
    id SERIAL PRIMARY KEY,
    source_file_id INTEGER REFERENCES source_files(id) ON DELETE CASCADE,
    vector_data VECTOR(1536) NOT NULL,
    snippet TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### File Organization in Blob Storage

```
container/
├── workspace_id_1/
│   ├── 20241201_123456_abc123_document1.pdf
│   └── 20241201_140000_def456_document2.docx
├── workspace_id_2/
│   └── 20241201_150000_ghi789_document3.txt
```

## Key Features

### ✅ Simplified Architecture

- No attachments table needed
- Direct blob path storage in `source_files.file_path`
- Workspace isolation through path prefixes

### ✅ Efficient Processing

- Direct Azure Blob upload (no server bandwidth usage)
- Synchronous processing confirmation
- Automatic vector generation and storage

### ✅ Workspace Isolation

- Documents organized by workspace_id prefix
- Workspace-specific search and listing
- Secure access controls

### ✅ File Management

- Generate temporary download URLs
- Delete documents (with optional blob deletion)
- Metadata from both RAG system and Blob Storage

## Testing

Run the test script to verify the workflow:

```bash
python test_rag_blob_workflow.py
```

This will:

1. Create a test workspace
2. Generate upload URL
3. Upload a test document
4. Confirm upload and process for RAG
5. List documents
6. Search documents
7. Generate download URL
8. Optionally delete the document

## Migration from Attachments

If you have existing attachments, you can migrate them:

1. **Copy blob paths**: `INSERT INTO source_files (file_path) SELECT azure_blob_path FROM attachments WHERE azure_blob_path IS NOT NULL`
2. **Process for RAG**: Use the existing `process_blob_file_for_rag` method for each file
3. **Update references**: Update any application code to use blob paths instead of attachment IDs

## Frontend Integration

```typescript
// 1. Generate upload URL
const uploadResponse = await api.post(
  `/rag/workspaces/${workspaceId}/documents/upload-url`,
  {
    fileName: file.name,
    fileSize: file.size,
    mimeType: file.type,
  }
);

const { uploadUrl, blobName } = uploadResponse.data;

// 2. Upload to Azure
await fetch(uploadUrl, {
  method: "PUT",
  headers: {
    "x-ms-blob-type": "BlockBlob",
    "Content-Type": file.type,
  },
  body: file,
});

// 3. Confirm and process
const processResponse = await api.post(
  `/rag/workspaces/${workspaceId}/documents/confirm-upload`,
  {
    blobName,
    fileName: file.name,
    replaceExisting: false,
  }
);

console.log("Document processed:", processResponse.data);
```

## Benefits

1. **Reduced Complexity**: No intermediate attachment records needed
2. **Better Performance**: Direct blob uploads, no server bottleneck
3. **Cost Effective**: Lower bandwidth usage on your servers
4. **Scalable**: Leverages Azure's global CDN and performance
5. **Workspace Isolation**: Built-in multi-tenancy support
6. **Flexible**: Easy to extend with additional metadata as needed
