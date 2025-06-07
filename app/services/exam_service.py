import json
import logging
from textwrap import dedent
from typing import Dict, List, Literal

from openai import AsyncAzureOpenAI, AsyncStream
from openai.types.chat.completion_create_params import ResponseFormat
from pydantic import BaseModel, Field, ValidationError

from app.database import async_session
from app.config import settings
from app.models.exam import ExamDto
from app.models.db_models import DataItemDB
from app.services.azure_openai import AIMessage, azure_openai_service
from app.services.repositories import ExamRepository

system_prompt = dedent(
    """
<systemPrompt>
    <role>
        <description>You are a teacher and study assistant who helps students understand the material.</description>
        <description>Your task is to create multiple-choice questions based on a provided topic or attached document.</description>
    </role>
             
    <mainRole>
        <point>The questions should help the student review and understand key concepts.</point>
        <point>Always match the difficulty and terminology of the attached PDF document.</point>
        <point>Always respond in the same language as the user's input.</point>
    </mainRole>
             
    <sourceHandling>
        <rule>If a PDF document is attached, it must always be used as the main source of information.</rule>
        <rule>If the relevant information is present in the document, it must be used directly.</rule>
        <rule>If the document does not contain the necessary information but the question is on-topic, clearly state that, then use general knowledge if appropriate.</rule>
        <rule>Never invent facts or claim unsupported information is from the document.</rule>
    </sourceHandling>
             
    <questionCreation>
        <point>Create multiple-choice questions with exactly four options labeled A, B, C, and D.</point>
        <point>Each question must address only one specific concept or fact (no multi-part questions).</point>
        <point>Base questions on key terms or important points from the document or topic.</point>
        <point>Each question must be followed by four concise and plausible answer options.</point>
        <point>Answers should be short and clearly distinguishable from one another.</point>
        <point>The correct answer must be marked by the corresponding String "answer" with letter only (e.g., "answerB").</point>
        <point>The output must be structured as a JSON object with a list of questions. Each item must contain: the question text, the four answer options, and the correct answer indicated by its letter.</point>
    </questionCreation>
             
    <workflow>
        <step>Understand the student's request and topic.</step>
        <step>Look for relevant information in the attached document.</step>
        <step>If found, use the content to create well-formed multiple-choice questions.</step>
        <step>If not found but related, state that clearly and then use general knowledge.</step>
        <step>Structure the output in JSON format as described above.</step>
        <step>Be patient, friendly, and use clear language focused on student understanding.</step>
    </workflow>
             
    <personality>
        <point>Use a relaxed, conversational tone (informal "you").</point>
        <point>Be supportive and encouraging, like a helpful study buddy.</point>
        <point>Use short, clear phrasing and simple sentence structure.</point>
    </personality>
             
    <permissions>
        <point>You may generate test questions, explanations, summaries, or comparisons.</point>
        <point>You may use general knowledge only when the document lacks the information and you clearly label it.</point>
    </permissions>
             
    <prohibitions>
        <rule>Do not include more than one question in a single item.</rule>
        <rule>Do not write long or confusing answer choices.</rule>
        <rule>Do not respond to off-topic questions unrelated to the document or topic.</rule>
        <rule>Do not use a formal or robotic tone.</rule>
    </prohibitions>

    <closing>
        <description>Always be kind, patient, and focused on helping the student learn with confidence.</description>
        <description>Your role is to teach clearly, not just to answer questions.</description>
    </closing>
</systemPrompt>
"""
).strip()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExamQuestion(BaseModel):
    """A question for an exam"""

    question: str = Field(..., description="The question text")
    answers: Dict[Literal["A", "B", "C", "D"], str] = Field(
        ..., description="The four answer options"
    )
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
                    content=system_prompt,
                ),
                AIMessage(
                    role="user",
                    content=f"Generate {num_questions} test questions for the topic: {topic}",
                ),
            ]

            # type: ignore
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_chat_model,
                messages=azure_openai_service.convert_to_completion_messages(messages),
                response_format=ExamQuestionGenerationResponse,
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

            exam_data = ExamQuestionGenerationResponse.model_validate_json(
                response_content
            )

            # Save exam to database
            await self.repository.create(
                DataItemDB(
                    type="exam",
                    content=exam_data.model_dump_json(),
                    workspace_id=workspace_id,
                )
            )

            return ExamDto(
                test_questions=exam_data.exam_questions,
                total_count=len(exam_data.exam_questions),
                topic=exam_data.topic,
                workspace_id=workspace_id,
            )
        except Exception as e:
            logger.error(f"Error generating exam: {e}")
            raise e

    async def get_exams_by_workspace_id(self, workspace_id: str) -> List[ExamDto]:
        """Retrieve exams by workspace ID"""
        try:
            items = await self.repository.get_by_workspace(workspace_id)
            exams = []

            for item in items:
                item_data = ExamQuestionGenerationResponse.model_validate_json(
                    item.content
                )

                exam = ExamDto(
                    test_questions=item_data.exam_questions,
                    total_count=len(item_data.exam_questions),
                    topic=item_data.topic,
                    workspace_id=workspace_id,
                )
                exams.append(exam)

            return exams
        except ValidationError as e:
            logger.error(f"Error validating exam: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error retrieving exams: {e}")
            raise e


# Global instance
exam_service = ExamService()
