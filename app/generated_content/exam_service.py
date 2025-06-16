import logging
from typing import Dict, List, Literal

from openai import AsyncAzureOpenAI, AsyncStream
from pydantic import BaseModel, Field, ValidationError

from app.database import async_session
from app.config import settings
from app.generated_content.constant import EXAM_SYSTEM_PROMPT
from app.generated_content.model import ExamDto, TestQuestionDto
from app.azure.openai_service import AIMessage, azure_openai_service
from app.generated_content.repository import ExamRepository
from app.generated_content.db import GeneratedContentDB


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExamQuestion(BaseModel):
    """A question for an exam"""

    question: str = Field(..., description="The question text")
    answerA: str = Field(..., description="The first answer option")
    answerB: str = Field(..., description="The second answer option")
    answerC: str = Field(..., description="The third answer option")
    answerD: str = Field(..., description="The fourth answer option")
    correct_answer: str = Field(..., description="The key to the correct answer")


class ExamQuestionGenerationResponse(BaseModel):
    """A response for an exam question generation"""

    exam_questions: List[ExamQuestion] = Field(
        ..., description="The list of exam questions"
    )
    topic: str = Field(..., description="The topic of the exam")


class ExamService:
    def __init__(self):
        # Validate config
        if not any(
            [
                settings.azure_openai_api_key,
                settings.azure_openai_endpoint,
                settings.azure_openai_chat_model,
            ]
        ):
            logger.error("Azure OpenAI is not configured")
            raise ValueError("Azure OpenAI is not configured")

        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version="2024-12-01-preview",
            azure_endpoint=settings.azure_openai_endpoint,
        )

        self.repository = ExamRepository(async_session())

    async def generate_exam(
        self, topic: str, workspace_id: str, num_questions: int = 5
    ) -> ExamDto:
        """Generate exam questions for a given topic with structured output"""

        try:
            # Create messages
            messages = [
                AIMessage(
                    role="system",
                    content=EXAM_SYSTEM_PROMPT,
                ),
                AIMessage(
                    role="user",
                    content=f"Generate {num_questions} test questions for the topic: {topic}",
                ),
            ]

            # type: ignore
            response = await self.client.beta.chat.completions.parse(
                model=settings.azure_openai_chat_model,
                messages=azure_openai_service.convert_to_completion_messages(messages),
                response_format=ExamQuestionGenerationResponse,
                temperature=0.7,
                max_tokens=4000,
            )

            if isinstance(response, AsyncStream):
                logger.error("Streaming is not supported")
                raise ValueError("Streaming is not supported")

            response_content = response.choices[0].message.content
            if not response_content:
                logger.error("No response content received")
                raise ValueError("No response content received")

            exam_data = ExamQuestionGenerationResponse.model_validate_json(
                response_content
            )

            # Save exam to database
            generated_content = await self.repository.create(
                GeneratedContentDB(
                    type="exam",
                    content=exam_data.model_dump_json(),
                    workspace_id=workspace_id,
                )
            )

            return self._map_generated_content_to_dto(generated_content)
        except Exception as e:
            logger.error(f"Error generating exam: {e}")
            raise e

    async def get_exams_by_workspace_id(self, workspace_id: str) -> List[ExamDto]:
        """Retrieve exams by workspace ID"""
        try:
            items = await self.repository.get_by_workspace_id(workspace_id)

            return [self._map_generated_content_to_dto(item) for item in items]
        except ValidationError as e:
            logger.error(f"Error validating exam: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error retrieving exams: {e}")
            raise e

    def _map_generated_content_to_dto(
        self, generated_content: GeneratedContentDB
    ) -> ExamDto:
        item_data = ExamQuestionGenerationResponse.model_validate_json(
            generated_content.content
        )

        items: list[TestQuestionDto] = [
            TestQuestionDto(
                question=item.question,
                answers={
                    "A": item.answerA,
                    "B": item.answerB,
                    "C": item.answerC,
                    "D": item.answerD,
                },
                correct_answer=item.correct_answer,
            )
            for item in item_data.exam_questions
        ]

        return ExamDto(
            items=items,
            total_count=len(items),
            topic=item_data.topic,
            workspace_id=generated_content.workspace_id,
        )


# Global instance
exam_service = ExamService()
