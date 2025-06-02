from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import json
import uuid
from app.models import ChatSession, ChatMessage
from app.schemas import ChatSessionCreate, ChatMessageCreate, ChatResponse
from app.services.azure_openai import azure_openai
from app.services.document_service import DocumentService


class ChatService:
    
    @staticmethod
    async def create_session(db: AsyncSession, session_data: ChatSessionCreate) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_id=session_data.user_id,
            title=session_data.title or "New Chat"
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    
    @staticmethod
    async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Optional[ChatSession]:
        """Get chat session by ID"""
        query = select(ChatSession).where(
            ChatSession.id == session_id, 
            ChatSession.is_active == True
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_session_messages(db: AsyncSession, session_id: uuid.UUID) -> List[ChatMessage]:
        """Get all messages for a session"""
        query = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def add_message(
        db: AsyncSession, 
        session_id: uuid.UUID, 
        role: str, 
        content: str,
        metadata: Dict[str, Any] = None
    ) -> ChatMessage:
        """Add a message to a chat session"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata=json.dumps(metadata) if metadata else None
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    @staticmethod
    async def generate_rag_response(
        db: AsyncSession,
        session_id: uuid.UUID,
        user_message: str,
        search_limit: int = 5
    ) -> ChatResponse:
        """Generate RAG response for user message"""
        
        # Add user message to session
        await ChatService.add_message(db, session_id, "user", user_message)
        
        # Search for relevant context
        search_results = await DocumentService.search_similar_chunks(
            db, user_message, search_limit
        )
        
        # Get conversation history
        messages = await ChatService.get_session_messages(db, session_id)
        
        # Build context from search results
        context_chunks = []
        sources = []
        
        for result in search_results:
            if result.score > 0.7:  # Only use high-confidence results
                context_chunks.append(f"Source: {result.document_title}\n{result.content}")
                sources.append({
                    "title": result.document_title,
                    "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                    "source": result.source,
                    "score": result.score
                })
        
        context = "\n\n".join(context_chunks)
        
        # Build conversation history for context
        conversation_history = []
        for msg in messages[-10:]:  # Last 10 messages for context
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Create system prompt with context
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
        openai_messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent conversation history (excluding the system messages)
        for msg in conversation_history:
            if msg["role"] != "system":
                openai_messages.append(msg)
        
        # Generate response
        try:
            response_content = await azure_openai.chat_completion(openai_messages)
            
            # Add assistant response to session
            metadata = {"sources": sources} if sources else None
            await ChatService.add_message(
                db, session_id, "assistant", response_content, metadata
            )
            
            return ChatResponse(
                message=response_content,
                sources=sources,
                session_id=session_id
            )
            
        except Exception as e:
            error_message = "I apologize, but I'm having trouble generating a response right now. Please try again."
            await ChatService.add_message(db, session_id, "assistant", error_message)
            
            return ChatResponse(
                message=error_message,
                sources=[],
                session_id=session_id
            )
    
    @staticmethod
    async def get_user_sessions(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 20) -> List[ChatSession]:
        """Get all sessions for a user"""
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all() 