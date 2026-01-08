from pathlib import Path
from pydantic_settings import BaseSettings

class settings(BaseSettings):
    GEMINI_API_KEY: str  | None = None
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME: str  | None = None
    AZURE_OPENAI_EMBEDDING_VERSION: str  | None = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: str  | None = None
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: str  | None = None
    AZURE_OPENAI_API_VERSION: str  | None = None
    AZURE_OPENAI_ENDPOINT: str  | None = None
    AZURE_OPENAI_API_KEY: str  | None = None
    AZURE_OPENAI_DEPLOYMENT_NAME: str  | None = None

    class Config:
        env_file = ".env"
        extra = "allow"   


def get_setting():
    return settings()