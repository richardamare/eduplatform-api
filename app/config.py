import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    api_title: str = "Education Platform API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # Azure Configuration
    azure_key_vault_url: str = ""
    openai_api_key: str = ""
    
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://account:1dJd5U*kQzvn@ULMAGtHgl1@postgressqlvector.postgres.database.azure.com:5432/postgres?sslmode=require")
    database_echo: bool = False
    
    # Azure OpenAI
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    
    # App settings
    max_tokens: int = 4000
    temperature: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings() 