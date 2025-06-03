import json
from textwrap import dedent
from typing import List
from openai import AsyncAzureOpenAI

from app.config import settings
from app.models.flashcard import Flashcard, FlashcardDto
from app.models.db_models import DataItemDB
from app.database import async_session


class FlashcardService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version='2024-12-01-preview',
            azure_endpoint=settings.azure_openai_endpoint
        )
        
        self.system_prompt = dedent('''
            You are a helpful educational assistant. You will be provided with a topic or subject area,
            and your goal will be to generate relevant flashcard questions and answers.
            Create questions that test understanding, recall, and application of key concepts.
            Each question should be clear and concise, with accurate and comprehensive answers.
            Generate multiple flashcards for the given topic to cover different aspects.
        ''').strip()

    async def generate_flashcards(self, topic: str, workspace_id: str, num_cards: int = 5) -> FlashcardDto:
        """Generate flashcards for a given topic using OpenAI API with structured output"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_chat_model,
                messages=[
                    {
                        "role": "system", 
                        "content": self.system_prompt
                    },
                    {
                        "role": "user", 
                        "content": f"Generate {num_cards} flashcards for the topic: {topic}"
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "flashcard_generation",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "flashcards": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "question": {"type": "string"},
                                            "answer": {"type": "string"}
                                        },
                                        "required": ["question", "answer"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["flashcards"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.7,
                max_tokens=4000
            )
            
            # Parse the structured response
            flashcard_data = json.loads(response.choices[0].message.content)
            
            # Convert to Flashcard objects
            flashcards = [
                Flashcard(question=card["question"], answer=card["answer"])
                for card in flashcard_data["flashcards"]
            ]
            
            # Save flashcards to database
            await self._save_flashcards_to_db(flashcards, topic, workspace_id)
            
            return FlashcardDto(
                flashcards=flashcards,
                totalCount=len(flashcards),
                topic=topic,
                workspaceId=workspace_id
            )
            
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            raise Exception(f"Failed to generate flashcards: {str(e)}")

    async def _save_flashcards_to_db(self, flashcards: List[Flashcard], topic: str, workspace_id: str):
        """Save generated flashcards to the database as DataItems"""
        try:

            # Convert Flashcard objects to dictionaries
            flashcard_dicts = [
                {"question": fc.question, "answer": fc.answer}
                for fc in flashcards
            ]
            
            row = {
              "type": "flashcard",
              "content": json.dumps({
                "flashcards": flashcard_dicts,
                "topic": topic,
              }),
              "workspace_id": workspace_id
            }

            async with async_session() as session:
                data_item = DataItemDB(**row)
                session.add(data_item)
                await session.commit()
                print(f"Saved {len(flashcards)} flashcards to database for topic: {topic}")
                
        except Exception as e:
            print(f"Error saving flashcards to database: {e}")
            # Don't raise the exception here - we still want to return the flashcards
            # even if saving fails

    async def get_workspace_data_items(self, workspace_id: str, item_type: str = None) -> List[DataItemDB]:
        """Retrieve all data items for a workspace, optionally filtered by type"""
        try:
            async with async_session() as session:
                from sqlalchemy import select
                
                # Base query for workspace
                query = select(DataItemDB).where(DataItemDB.workspace_id == workspace_id)
                
                # Filter by type if provided
                if item_type:
                    query = query.where(DataItemDB.type == item_type)
                
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            print(f"Error retrieving data items: {e}")
            return []

    async def get_saved_flashcards(self, workspace_id: str) -> List[FlashcardDto]:
        """Retrieve saved flashcards from database, optionally filtered by topic"""
        try:
            # Get flashcard data items
            data_items = await self.get_workspace_data_items(workspace_id, "flashcard")
            
            flashcard_dtos = []
            for item in data_items:
                try:
                    content = json.loads(item.content)
                    flashcards = []
                    
                    # Handle new format where all flashcards are in one item
                    if "flashcards" in content:
                        for fc_data in content["flashcards"]:
                            flashcard = Flashcard(
                                question=fc_data["question"],
                                answer=fc_data["answer"]
                            )
                            flashcards.append(flashcard)
                    # Handle old format (single flashcard per item) for backward compatibility
                    elif "question" in content and "answer" in content:
                        flashcard = Flashcard(
                            question=content["question"],
                            answer=content["answer"]
                        )
                        flashcards.append(flashcard)
                    
                    if flashcards:  # Only create DTO if we have flashcards
                        flashcard_dto = FlashcardDto(
                            flashcards=flashcards,
                            totalCount=len(flashcards),
                            topic=content.get('topic', 'Unknown'),
                            workspaceId=workspace_id
                        )
                        flashcard_dtos.append(flashcard_dto)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing flashcard content: {e}")
                    continue
            
            return flashcard_dtos
                
        except Exception as e:
            print(f"Error retrieving flashcards: {e}")
            return []


# Global instance
flashcard_service = FlashcardService() 