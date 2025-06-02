# Simple Streaming Chat API

A minimal FastAPI application that provides streaming chat responses using Azure OpenAI.

## Features

- Single streaming chat endpoint
- Azure OpenAI integration
- CORS enabled for web clients
- Minimal dependencies

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**

   ```bash
   cp env.example .env
   ```

   Edit `.env` with your Azure OpenAI credentials:

   ```
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo
   ```

3. **Run the server:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## API Usage

### Stream Chat Response

**POST** `/api/v1/chat/stream`

Request body:

```json
{
  "message": "Hello, how are you?"
}
```

Response: Server-sent events stream

```
data: {"content": "Hello"}
data: {"content": "! I'm"}
data: {"content": " doing"}
data: {"content": " well"}
data: {"done": true}
```

### Example with curl:

```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
     -H "Content-Type: application/json" \
     -d '{"message": "Tell me a joke"}' \
     --no-buffer
```

### Example with JavaScript:

```javascript
const response = await fetch("/api/v1/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Hello!" }),
});

const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = new TextDecoder().decode(value);
  const lines = chunk.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      if (data.content) {
        console.log(data.content);
      } else if (data.done) {
        console.log("Stream complete");
      }
    }
  }
}
```

## Health Check

**GET** `/health` - Returns `{"status": "healthy"}`

## Development

Start with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
