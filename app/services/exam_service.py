import json
from textwrap import dedent
from typing import List
from openai import AsyncAzureOpenAI

from app.config import settings
from app.models.exam import TestQuestion, ExamDto
from app.models.db_models import DataItemDB
from app.database import async_session


class ExamService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version='2024-12-01-preview',
            azure_endpoint=settings.azure_openai_endpoint
        )
        
        self.system_prompt = dedent('''
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
        ''').strip()

    async def generate_exam(self, topic: str, workspace_id: str, num_questions: int = 5) -> ExamDto:
        """Generate exam questions for a given topic using OpenAI API with structured output"""
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
                        "content": f"Generate {num_questions} test questions for the topic: {topic}"
                    }
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "test_question_generation",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "test_question": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "question": {"type": "string"},
                                            "answerA": {"type": "string"},
                                            "answerB": {"type": "string"},
                                            "answerC": {"type": "string"},
                                            "answerD": {"type": "string"},
                                            "correct_answer": {"type": "string"}
                                        },
                                        "required": ["question", "answerA", "answerB", "answerC", "answerD", "correct_answer"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["test_question"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                temperature=0.7,
                max_tokens=4000
            )
            
            # Parse the structured response
            exam_data = json.loads(response.choices[0].message.content)
            
            # Convert to TestQuestion objects using the alias names
            test_questions = []
            for q in exam_data["test_question"]:
                test_question = TestQuestion.model_validate({
                    "question": q["question"],
                    "answerA": q["answerA"],
                    "answerB": q["answerB"],
                    "answerC": q["answerC"],
                    "answerD": q["answerD"],
                    "correct_answer": q["correct_answer"]
                })
                test_questions.append(test_question)
            
            # Save exam to database
            await self._save_exam_to_db(test_questions, topic, workspace_id)
            
            return ExamDto(
                test_questions=test_questions,
                total_count=len(test_questions),
                topic=topic,
                workspace_id=workspace_id
            )
            
        except Exception as e:
            print(f"Error generating exam: {e}")
            raise Exception(f"Failed to generate exam: {str(e)}")

    async def _save_exam_to_db(self, test_questions: List[TestQuestion], topic: str, workspace_id: str):
        """Save generated exam to the database as DataItems"""
        try:
            # Convert TestQuestion objects to dictionaries
            question_dicts = [
                {
                    "question": q.question,
                    "answerA": q.answer_a,
                    "answerB": q.answer_b,
                    "answerC": q.answer_c,
                    "answerD": q.answer_d,
                    "correct_answer": q.correct_answer
                }
                for q in test_questions
            ]
            
            row = {
                "type": "exam",
                "content": json.dumps({
                    "test_questions": question_dicts,
                    "topic": topic,
                }),
                "workspace_id": workspace_id
            }

            async with async_session() as session:
                data_item = DataItemDB(**row)
                session.add(data_item)
                await session.commit()
                print(f"Saved {len(test_questions)} exam questions to database for topic: {topic}")
                
        except Exception as e:
            print(f"Error saving exam to database: {e}")
            # Don't raise the exception here - we still want to return the exam
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

    async def get_saved_exams(self, workspace_id: str) -> List[ExamDto]:
        """Retrieve saved exams from database"""
        try:
            # Get exam data items
            data_items = await self.get_workspace_data_items(workspace_id, "exam")
            
            exam_dtos = []
            for item in data_items:
                try:
                    content = json.loads(item.content)
                    test_questions = []
                    
                    # Handle format where all questions are in one item
                    if "test_questions" in content:
                        for q_data in content["test_questions"]:
                            test_question = TestQuestion.model_validate({
                                "question": q_data["question"],
                                "answerA": q_data["answerA"],
                                "answerB": q_data["answerB"],
                                "answerC": q_data["answerC"],
                                "answerD": q_data["answerD"],
                                "correct_answer": q_data["correct_answer"]
                            })
                            test_questions.append(test_question)
                    
                    if test_questions:  # Only create DTO if we have questions
                        exam_dto = ExamDto(
                            test_questions=test_questions,
                            total_count=len(test_questions),
                            topic=content.get('topic', 'Unknown'),
                            workspace_id=workspace_id
                        )
                        exam_dtos.append(exam_dto)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error parsing exam content: {e}")
                    continue
            
            return exam_dtos
                
        except Exception as e:
            print(f"Error retrieving exams: {e}")
            return []


# Global instance
exam_service = ExamService() 