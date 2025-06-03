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
            system_prompt = """
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