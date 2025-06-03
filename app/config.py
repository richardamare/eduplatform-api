import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    
    # App settings
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Chat settings
    max_tokens: int = 4000
    temperature: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings() 