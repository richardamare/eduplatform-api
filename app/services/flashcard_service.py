from textwrap import dedent
from typing import List
from openai import AsyncAzureOpenAI, AsyncStream
import logging

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.models.flashcard import FlashcardDto
from app.models.db_models import DataItemDB
from app.database import async_session
from app.services.azure_openai import AIMessage, azure_openai_service
from app.services.repositories import FlashcardRepository


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

system_prompt = dedent(
    """
    You are a helpful educational assistant. You will be provided with a topic or subject area,
    and your goal will be to generate relevant flashcard questions and answers.
    Create questions that test understanding, recall, and application of key concepts.
    Each question should be clear and concise, with accurate and comprehensive answers.
    Generate multiple flashcards for the given topic to cover different aspects.
"""
).strip()


class FlashcardItem(BaseModel):
    question: str
    answer: str


class FlashcardGenerationResponse(BaseModel):
    items: List[FlashcardItem]
    topic: str


class FlashcardService:
    def __init__(self):
        if not any(
            [
                settings.azure_openai_api_key,
                settings.azure_openai_endpoint,
                settings.azure_openai_chat_model,
            ]
        ):
            raise ValueError("Azure OpenAI configuration is not set")

        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version="2024-12-01-preview",
            azure_endpoint=settings.azure_openai_endpoint,
        )

        self.repository = FlashcardRepository(async_session())

    async def generate_flashcards(
        self, topic: str, workspace_id: str, num_cards: int = 5
    ) -> FlashcardDto:
        """Generate flashcards for a given topic using OpenAI API with structured output"""

        try:

            messages = [
                AIMessage(role="system", content=system_prompt),
                AIMessage(
                    role="user",
                    content=f"Generate {num_cards} flashcards for the topic: {topic}",
                ),
            ]

            # type: ignore
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_chat_model,
                messages=azure_openai_service.convert_to_completion_messages(messages),
                response_format=FlashcardGenerationResponse,
                temperature=0.7,
                max_tokens=4000,
                stream=False,
            )

            if isinstance(response, AsyncStream):
                logger.error("Streaming is not supported")
                raise ValueError("Streaming is not supported")

            response_content = response.choices[0].message.content
            if not response_content:
                logger.error("No response content received")
                raise ValueError("No response content received")

            flashcard_data = FlashcardGenerationResponse.model_validate_json(
                response_content
            )

            # Save flashcards to database
            await self.repository.create(
                DataItemDB(
                    type="flashcard",
                    content=flashcard_data.model_dump_json(),
                    workspace_id=workspace_id,
                )
            )

            return FlashcardDto(
                items=flashcard_data.items,
                total_count=len(flashcard_data.items),
                topic=flashcard_data.topic,
                workspace_id=workspace_id,
            )
        except Exception as e:
            logger.error(f"Error generating flashcards: {e}")
            raise e

    async def get_flashcards_by_workspace_id(
        self, workspace_id: str
    ) -> List[FlashcardDto]:
        """Retrieve all data items for a workspace, optionally filtered by type"""
        try:
            items = await self.repository.get_by_workspace(workspace_id)

            flashcards = []
            for item in items:
                item_data = FlashcardGenerationResponse.model_validate_json(
                    item.content
                )

                flashcard_dto = FlashcardDto(
                    items=item_data.items,
                    total_count=len(item_data.items),
                    topic=item_data.topic,
                    workspace_id=workspace_id,
                )
                flashcards.append(flashcard_dto)

            return flashcards
        except ValidationError as e:
            logger.error(f"Error validating flashcards: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error retrieving flashcards: {e}")
            raise e


flashcard_service = FlashcardService()
