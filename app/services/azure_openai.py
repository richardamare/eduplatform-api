from openai import AsyncAzureOpenAI
from typing import List, Dict, Any
import asyncio
from app.config import settings


class AzureOpenAIService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=settings.azure_openai_embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=settings.azure_openai_embedding_deployment
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            raise
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """Generate chat completion"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=temperature or settings.temperature,
                max_tokens=max_tokens or settings.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error in chat completion: {e}")
            raise
    
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