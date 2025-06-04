from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from openai import AsyncOpenAI

from app.services.repositories import ChatRepository, MessageRepository, WorkspaceRepository, AttachmentRepository
from app.models.chat import ChatDto
from app.models.message import MessageDto, CreateMessagePayload, MessageRole
from app.models.workspace import WorkspaceDto
from app.models.attachment import AttachmentDto, AttachmentSearchResult
from app.config import settings

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.message_repo = MessageRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        self.attachment_repo = AttachmentRepository(db)
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def create_chat_with_context(self, workspace_id: str, name: str, initial_message: str) -> tuple[ChatDto, MessageDto]:
        """Create a new chat and add the initial user message"""
        # Verify workspace exists
        workspace = await self.workspace_repo.get_by_id(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        
        # Create chat
        chat = await self.chat_repo.create(name, workspace_id)
        
        # Add initial message
        user_message = await self.message_repo.create(
            chat.id, 
            CreateMessagePayload(role=MessageRole.USER, content=initial_message)
        )
        
        return chat, user_message

    async def get_chat_with_messages(self, chat_id: str) -> tuple[Optional[ChatDto], List[MessageDto]]:
        """Get chat and all its messages"""
        chat = await self.chat_repo.get_by_id(chat_id)
        messages = await self.message_repo.get_by_chat(chat_id) if chat else []
        return chat, messages

    async def add_message_with_ai_response(self, chat_id: str, user_message: str, use_rag: bool = True) -> tuple[MessageDto, MessageDto]:
        """Add user message and generate AI response with optional RAG"""
        # Verify chat exists
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ValueError("Chat not found")
        
        # Add user message
        user_msg = await self.message_repo.create(
            chat_id,
            CreateMessagePayload(role=MessageRole.USER, content=user_message)
        )
        
        # Generate AI response
        context = ""
        if use_rag:
            context = await self._get_rag_context(chat.workspace_id, user_message)
        
        ai_response = await self._generate_ai_response(chat_id, user_message, context)
        
        # Add AI message
        ai_msg = await self.message_repo.create(
            chat_id,
            CreateMessagePayload(role=MessageRole.ASSISTANT, content=ai_response)
        )
        
        return user_msg, ai_msg

    async def _get_rag_context(self, workspace_id: str, query: str, limit: int = 5) -> str:
        """Get relevant context from RAG documents and attachments using workspace-specific search"""
        try:
            from app.services.rag_service import RAGService
            
            context_parts = []
            
            # First, try to get context from RAG documents (blob storage files)
            try:
                rag_service = RAGService()
                rag_results = await rag_service.search_workspace_vectors(
                    db=self.db,
                    workspace_id=workspace_id,
                    query_text=query,
                    limit=limit,
                    min_similarity=0.5
                )
                
                for result in rag_results:
                    # Extract display name from blob path
                    display_name = result.file_path.split('/')[-1] if '/' in result.file_path else result.file_path
                    context_parts.append(f"From {display_name} (similarity: {result.similarity:.3f}):\n{result.snippet}")
                
                print(f"Found {len(rag_results)} RAG results for workspace {workspace_id}")
                
            except Exception as e:
                print(f"Error searching RAG documents: {e}")
            
            # If we have enough context from RAG, use it; otherwise supplement with attachments
            if len(context_parts) < limit:
                remaining_limit = limit - len(context_parts)
                
                # Generate embedding for the query
                embedding_response = await self.openai_client.embeddings.create(
                    input=query,
                    model="text-embedding-ada-002"
                )
                query_vector = embedding_response.data[0].embedding
                
                # Search for similar attachments
                similar_attachments = await self.attachment_repo.vector_similarity_search(
                    query_vector=query_vector,
                    workspace_id=workspace_id,
                    limit=remaining_limit,
                    similarity_threshold=0.5
                )
                
                for result in similar_attachments:
                    context_parts.append(f"From attachment {result.attachment.name} (similarity: {result.similarity_score:.3f})")
                
                print(f"Found {len(similar_attachments)} attachment results for workspace {workspace_id}")
            
            return "\n\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            print(f"Error getting RAG context: {e}")
            return ""

    async def _generate_ai_response(self, chat_id: str, user_message: str, context: str) -> str:
        """Generate AI response using OpenAI with optional context"""
        try:
            # Get recent chat history
            _, messages = await self.get_chat_with_messages(chat_id)
            
            # Build conversation history (last 10 messages)
            conversation = []
            for msg in messages[-10:]:
                conversation.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add system message with context if available
            system_content = "You are a helpful assistant."
            if context:
                system_content += f"\n\nRelevant context from documents:\n{context}"
            
            messages_for_ai = [{"role": "system", "content": system_content}] + conversation
            
            # Generate response
            response = await self.openai_client.chat.completions.create(
                model=settings.azure_openai_chat_model,
                messages=messages_for_ai,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."

    async def search_attachments_by_content(self, workspace_id: str, query: str, limit: int = 10) -> List[AttachmentSearchResult]:
        """Search attachments by content similarity"""
        try:
            # Generate embedding for the query
            embedding_response = await self.openai_client.embeddings.create(
                input=query,
                model="text-embedding-ada-002"
            )
            query_vector = embedding_response.data[0].embedding
            
            # Search for similar attachments
            return await self.attachment_repo.vector_similarity_search(
                query_vector=query_vector,
                workspace_id=workspace_id,
                limit=limit,
                similarity_threshold=0.5
            )
            
        except Exception as e:
            print(f"Error searching attachments: {e}")
            return [] 