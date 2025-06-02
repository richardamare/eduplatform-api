from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
import json
from app.database import get_db
from app.schemas import (
    ChatSessionCreate, ChatSessionResponse, 
    ChatMessageCreate, ChatResponse
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session"""
    try:
        session = await ChatService.create_session(db, session_data)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat session: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a chat session with messages"""
    session = await ChatService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Load messages
    messages = await ChatService.get_session_messages(db, session_id)
    session.messages = messages
    
    return session


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    user_id: str,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get all chat sessions for a user"""
    sessions = await ChatService.get_user_sessions(db, user_id, skip, limit)
    return sessions


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: uuid.UUID,
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get RAG response"""
    # Verify session exists
    session = await ChatService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    try:
        # Generate RAG response
        response = await ChatService.generate_rag_response(
            db, session_id, message.content
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )


@router.post("/sessions/{session_id}/stream")
async def send_message_stream(
    session_id: uuid.UUID,
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get streaming RAG response"""
    # Verify session exists
    session = await ChatService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    async def generate_stream():
        try:
            # Add user message to session
            await ChatService.add_message(db, session_id, "user", message.content)
            
            # Get context (similar to the non-streaming version)
            from app.services.document_service import DocumentService
            search_results = await DocumentService.search_similar_chunks(
                db, message.content, 5
            )
            
            # Build context
            context_chunks = []
            sources = []
            
            for result in search_results:
                if result.score > 0.7:
                    context_chunks.append(f"Source: {result.document_title}\n{result.content}")
                    sources.append({
                        "title": result.document_title,
                        "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                        "source": result.source,
                        "score": result.score
                    })
            
            context = "\n\n".join(context_chunks)
            
            # Get conversation history
            messages = await ChatService.get_session_messages(db, session_id)
            conversation_history = []
            for msg in messages[-10:]:
                if msg.role != "system":
                    conversation_history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Create system prompt
            system_prompt = f"""You are a helpful AI assistant with access to a knowledge base. 
Use the following context to answer the user's question. If the context doesn't contain 
relevant information, say so and provide a helpful response based on your general knowledge.

Context from knowledge base:
{context}

Instructions:
- Be concise and accurate
- Cite sources when using information from the context
- If you're unsure about something, say so
- Provide helpful and relevant information"""
            
            # Prepare messages for OpenAI
            from app.services.azure_openai import azure_openai
            openai_messages = [{"role": "system", "content": system_prompt}]
            openai_messages.extend(conversation_history)
            
            # Generate streaming response
            full_response = ""
            async for chunk in azure_openai.chat_completion_stream(openai_messages):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
            
            # Send sources
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # Save assistant response
            metadata = {"sources": sources} if sources else None
            await ChatService.add_message(
                db, session_id, "assistant", full_response, metadata
            )
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    ) 