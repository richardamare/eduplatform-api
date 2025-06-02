from openai import AsyncAzureOpenAI
from typing import List, Dict
from app.config import settings


class AzureOpenAIService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
    
    async def chat_completion_stream(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = None,
        max_tokens: int = None
    ):
        """Generate streaming chat completion"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=temperature or settings.temperature,
                max_tokens=max_tokens or settings.max_tokens,
                stream=True
            )
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"Error in streaming chat completion: {e}")
            raise


# Global instance
azure_openai = AzureOpenAIService() 