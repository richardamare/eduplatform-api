from openai import AsyncAzureOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionChunk,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from typing import List, Optional, Union, Literal
import logging

from pydantic import BaseModel
from app.config import settings


class AIMessage(BaseModel):
    role: Union[str, Literal["system", "user", "assistant"]]
    content: str

    def to_dict(self):
        return {"role": self.role, "content": self.content}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Service for interacting with Azure OpenAI for chat completions"""

    def __init__(self):
        # Validate that we have required config
        if not all(
            [
                settings.azure_openai_api_key,
                settings.azure_openai_endpoint,
                settings.azure_openai_chat_model,
                settings.azure_openai_embedding_model,
            ]
        ):
            logger.error("Missing Azure OpenAI configuration")
            raise ValueError("Missing Azure OpenAI configuration")

        print("settings.azure_openai_api_key", settings.azure_openai_api_key)
        print("settings.azure_openai_endpoint", settings.azure_openai_endpoint)
        print("settings.azure_openai_chat_model", settings.azure_openai_chat_model)
        print(
            "settings.azure_openai_embedding_model",
            settings.azure_openai_embedding_model,
        )

        # Initialize the client
        self.client = AsyncAzureOpenAI(
            api_key="BnFWGEUTOT7R7GTocrq96v50Ubyx0pXre9TzoVTDcwknxwpW5hLeJQQJ99BFACHYHv6XJ3w3AAAAACOGoP7J",
            api_version="2024-12-01-preview",
            azure_endpoint="https://richa-mbp0u9iy-eastus2.cognitiveservices.azure.com/",
        )

    async def chat_completion_stream(
        self,
        messages: List[AIMessage],
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """Generate streaming chat completion with optional RAG context"""

        try:
            # Prepare messages with optional context injection
            processed_messages = messages.copy()

            # If context is provided, inject it as an assistant message
            if context is not None:
                # Find the last system message index, or insert at beginning
                last_system_msg_idx = -1
                for i, msg in enumerate(processed_messages):
                    if msg.role == "system":
                        last_system_msg_idx = i

                # Insert context after system message (or at beginning if no system message)
                context_message = AIMessage(role="assistant", content=context)
                processed_messages.insert(last_system_msg_idx + 1, context_message)

            # Create the response
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_chat_model,
                messages=self.convert_to_completion_messages(processed_messages),
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            if isinstance(response, AsyncStream):
                async for chunk in response:
                    if isinstance(chunk, ChatCompletionChunk):
                        for choice in chunk.choices[:1]:
                            if hasattr(choice, "delta") and choice.delta:
                                if (
                                    hasattr(choice.delta, "content")
                                    and choice.delta.content
                                ):
                                    yield choice.delta.content

        except Exception as e:
            logger.error(f"Error in streaming chat completion: {e}")
            yield f"Error: {str(e)}"

    def convert_to_completion_messages(self, messages: List[AIMessage]) -> List[
        Union[
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
            ChatCompletionAssistantMessageParam,
        ]
    ]:
        completion_messages: List[
            Union[
                ChatCompletionSystemMessageParam,
                ChatCompletionUserMessageParam,
                ChatCompletionAssistantMessageParam,
            ]
        ] = []
        for msg in messages:
            if msg.role == "system":
                completion_messages.append(
                    ChatCompletionSystemMessageParam(role="system", content=msg.content)
                )
            elif msg.role == "user":
                completion_messages.append(
                    ChatCompletionUserMessageParam(role="user", content=msg.content)
                )
            elif msg.role == "assistant":
                completion_messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant", content=msg.content
                    )
                )
        return completion_messages


# Global instance
azure_openai_service = AzureOpenAIService()
