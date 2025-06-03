from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import json
from app.services.azure_openai import azure_openai
from app.services.rag_service import RAGService
from app.database import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


@router.post("/stream")
async def chat_stream(chat_message: ChatMessage, db: AsyncSession = Depends(get_db)):
    """Streaming chat endpoint with RAG context"""
    
    async def generate_stream():
        try:
            # Simple system prompt
            system_prompt = "You are a helpful AI assistant. Be concise and helpful."
            
            # Initialize RAG service
            rag_service = RAGService()
            
            # Search for relevant context using vector similarity
            context = ""
            try:
                search_results = await rag_service.search_similar_vectors(
                    db, 
                    chat_message.message, 
                    limit=3,  # Get top 3 most similar chunks
                    min_similarity=0.5  # Only include results with >50% similarity
                )
                
                if search_results:
                    # Combine the most relevant contexts
                    context_chunks = []
                    for result in search_results:
                        context_chunks.append(f"From {result.file_path} (similarity: {result.similarity:.2f}):\n{result.snippet}")
                    
                    context = "\n\n".join(context_chunks)
                    print(f"Found {len(search_results)} relevant contexts for query: {chat_message.message}")
                else:
                    print("No relevant context found for query")
                    
            except Exception as e:
                print(f"Error searching for context: {e}")
                # Continue without context if search fails
            
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_message.message}
            ]

            print('context', context)
            
            # Generate streaming response with context
            async for chunk in azure_openai.chat_completion_stream(messages, context=context):
                print(chunk)
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    ) 