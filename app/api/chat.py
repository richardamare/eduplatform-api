from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from app.services.azure_openai import azure_openai

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


@router.post("/stream")
async def chat_stream(chat_message: ChatMessage):
    """Simple streaming chat endpoint"""
    
    async def generate_stream():
        try:
            # Simple system prompt
            system_prompt = "You are a helpful AI assistant. Be concise and helpful."
            
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chat_message.message}
            ]
            
            # Generate streaming response
            async for chunk in azure_openai.chat_completion_stream(messages):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    ) 