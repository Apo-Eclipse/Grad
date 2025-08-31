from pathlib import Path
from pydantic_settings import BaseSettings , SettingsConfigDict

class settings(BaseSettings):
    
    GEMINI_API_KEY: str
    
    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / "env" / ".env")


def get_setting():
    return settings()