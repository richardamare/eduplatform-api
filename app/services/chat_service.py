import json
import logging
import re
from textwrap import dedent
from typing import AsyncGenerator, List, Optional

from app.models.chat import ChatDto
from app.models.db_models import ChatDB, MessageDB
from app.models.message import MessageDto, MessageRole
from app.services.azure_openai import AIMessage, azure_openai_service
from app.services.rag_service import rag_service
from app.services.repositories import ChatRepository, MessageRepository
from app.database import async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

system_prompt = dedent(
    """
You are a dedicated study assistant helping a student learn from a provided PDF document. 
You will be working with this document as your primary source of truth. 
The student may ask you to explain, summarize, quiz them, or create study materials. 
Your main role is to help the student deeply understand the material.
Actively teach and guide the student. Don’t just answer questions — explain concepts clearly, provide examples, offer comparisons, and create summaries or test questions when needed. 
Break down complex ideas into simple parts. Use structured, easy-to-follow formats (like bullet points, headings, and tables).

You MUST ALWAYS search for the answer in the PDF first.
- If the information is found in the PDF, use it as the source.
- If the information is NOT found in the PDF, say so clearly (e.g., “This information was not found in the provided document.”)
    - Then, and only then, you may respond using general knowledge (from your training data) or, if allowed by the system, up-to-date internet-based information — but you must clearly label it as external knowledge.

You must never invent facts as if they came from the PDF.

## Personality
You are a friendly, patient, and supportive study buddy.
Always speak casually, use “you” (in czech "tykáš"), and keep your tone warm and encouraging — like a helpful friend who wants the student to succeed.

You should:
- speak in a relaxed, conversational tone
- use informal language (but stay respectful and professional)
- be encouraging, especially when the student struggles


## Workflow
### High-Level Strategy
1. Read and understand the student’s request.
2. Search the PDF for relevant information.
3. If found, respond using PDF content.
4. If not found, explicitly say the PDF does not contain the requested information, then answer using general knowledge if appropriate.
5. Provide additional explanations, examples, or comparisons as needed.
6. If requested, generate structured outputs: summaries, tests, outlines, etc.
7. Ensure the student understands. Keep explaining if needed.

### You Must Always:
- Prioritize the PDF as the main source
- If the PDF lacks the info, say so explicitly
- Distinguish external knowledge with clear labeling
- Use structured formats (bullet points, tables, headings)
- Speak in clear, student-friendly language
- Never stop at simply providing an answer — your goal is deep student understanding.

### You Can:
- Create summaries, outlines, test questions, or flashcards
- Explain or compare concepts
- Use Socratic questioning to test understanding
- Supplement explanations with general knowledge only if the PDF lacks relevant info, and you label it properly

Be patient, clear, and focused on the student's learning. Your role is to teach, not just to answer.
"""
).strip()


class ChatService:
    def __init__(self):
        self.chat_repository = ChatRepository(async_session())
        self.message_repository = MessageRepository(async_session())

    async def create_chat(self, name: str, workspace_id: str) -> ChatDto:
        chat = await self.chat_repository.create(name, workspace_id)
        return self._map_chat_to_dto(chat)

    async def get_by_id(self, chat_id: str) -> Optional[ChatDto]:
        chat = await self.chat_repository.get_by_id(chat_id)
        if not chat:
            return None
        return self._map_chat_to_dto(chat)

    async def get_messages_by_chat_id(self, chat_id: str) -> List[MessageDto]:
        messages = await self.message_repository.get_by_chat_id(chat_id)
        return [self._map_message_to_dto(message) for message in messages]

    async def get_chats_by_workspace_id(self, workspace_id: str) -> List[ChatDto]:
        chats = await self.chat_repository.get_by_workspace(workspace_id)
        return [self._map_chat_to_dto(chat) for chat in chats]

    async def stream(
        self, user_message: str, chat_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response"""
        try:
            existing_chat = await self.chat_repository.get_by_id(chat_id)
            if not existing_chat:
                raise Exception("Chat not found")

            await self.message_repository.create(
                MessageDB(
                    content=user_message,
                    role=MessageRole.USER,
                    chat_id=chat_id,
                )
            )

            return self._generate_stream(
                user_message=user_message,
                workspace_id=existing_chat.workspace_id,
                chat_id=chat_id,
            )
        except Exception as e:
            logger.error(f"Error streaming chat: {e}")
            raise

    async def _generate_stream(
        self, user_message: str, workspace_id: str, chat_id: str
    ) -> AsyncGenerator[str, None]:
        try:
            assistant_content = ""
            context = ""

            try:
                search_results = await rag_service.search_similar_vectors(
                    query_text=user_message,
                    workspace_id=workspace_id,
                    limit=3,
                    min_similarity=0.5,
                )

                if search_results:
                    context_chunks: List[str] = []

                    for result in search_results:
                        chunk = f"From {result.file_path} (similarity: {result.similarity:.2f}):\n{result.content_text}"
                        context_chunks.append(chunk)

                    context = "\n\n".join(context_chunks)
                    print(
                        f"Found {len(search_results)} relevant contexts for query: {user_message}"
                    )
            except Exception as e:
                logger.error(f"Error searching for context: {e}")
                # Continue without context if search fails

            messages = [
                AIMessage(role="system", content=system_prompt),
                AIMessage(role="user", content=user_message),
            ]

            async for chunk in azure_openai_service.chat_completion_stream(
                messages=[*messages],
                context=context,
            ):
                assistant_content += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            try:
                assistant_msg = await self.message_repository.create(
                    MessageDB(
                        chat_id=chat_id,
                        role=MessageRole.ASSISTANT,
                        content=assistant_content,
                    )
                )

                try:
                    message_count = await self.message_repository.count_by_chat(chat_id)
                    if message_count == 2 and assistant_content.strip():
                        new_name = self._generate_chat_name(assistant_content)
                        await self.chat_repository.update_name(chat_id, new_name)
                        print(f"Updated chat name to: {new_name}")
                except Exception as name_error:
                    logger.error(f"Failed to update chat name: {name_error}")
            except Exception as e:
                logger.error(f"Failed to store assistant message: {e}")

            yield f"data: {json.dumps({'done': True, 'chat_id': chat_id})}\n\n"
        except Exception as e:
            if assistant_content.strip():
                try:
                    assistant_msg = await self.message_repository.create(
                        MessageDB(
                            chat_id=chat_id,
                            role=MessageRole.ASSISTANT,
                            content=assistant_content,
                        )
                    )
                    print(f"Stored partial assistant message: {assistant_msg.id}")
                except Exception as storage_error:
                    logger.error(
                        f"Failed to store partial assistant message: {storage_error}"
                    )

            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def _generate_chat_name(self, ai_response: str) -> str:
        """Generate a meaningful chat name from AI response"""
        if not ai_response.strip():
            return "New Chat"

        # Extract a meaningful name from the AI response
        sentences = re.split(r"[.!?]", ai_response)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return "New Chat"

        first_sentence = sentences[0].strip()

        # Remove common starting phrases
        clean_sentence = re.sub(
            r"^(I understand|Let me help|Here\'s|This is|I can help|Sure|Of course|Certainly)\s*,?\s*",
            "",
            first_sentence,
            flags=re.IGNORECASE,
        )

        # Take first few words and clean up
        words = clean_sentence.split()
        title_words = words[: min(5, len(words))]

        if not title_words:
            return "New Chat"

        title = " ".join(title_words)

        # Ensure it's not too long and ends properly
        if len(title) > 50:
            title = title[:47] + "..."

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:] if len(title) > 1 else title.upper()

        return title

    def _map_chat_to_dto(self, chat: ChatDB) -> ChatDto:
        return ChatDto(
            id=chat.id,
            name=chat.name,
            workspace_id=chat.workspace_id,
            created_at=chat.created_at,
        )

    def _map_message_to_dto(self, message: MessageDB) -> MessageDto:
        return MessageDto(
            id=message.id,
            chat_id=message.chat_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )


chat_service = ChatService()
