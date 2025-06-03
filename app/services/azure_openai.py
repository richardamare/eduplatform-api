from openai import AsyncAzureOpenAI
from typing import List, Dict
from app.config import settings


class AzureOpenAIService:
    def __init__(self):
        print(settings)
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
            # Validate that we have required config
            if not all([
                settings.azure_openai_api_key,
                settings.azure_openai_endpoint,
                settings.azure_openai_deployment_name
            ]):
                raise ValueError("Missing Azure OpenAI configuration")
                
            response = await self.client.chat.completions.create(
                model=settings.azure_openai_deployment_name,
                messages=messages,
                temperature=temperature or settings.temperature,
                max_tokens=max_tokens or settings.max_tokens,
                stream=True
            )
            
            async for chunk in response:
                # Check if chunk has choices and the first choice has delta content
                if (hasattr(chunk, 'choices') and 
                    chunk.choices and 
                    len(chunk.choices) > 0 and 
                    hasattr(chunk.choices[0], 'delta') and 
                    chunk.choices[0].delta and 
                    hasattr(chunk.choices[0].delta, 'content') and 
                    chunk.choices[0].delta.content):
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"Error in streaming chat completion: {e}")
            yield f"Error: {str(e)}"


# Global instance
azure_openai = AzureOpenAIService() 