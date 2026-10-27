from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = 'mysql+pymysql://sentinel_user:CHANGE_ME@127.0.0.1:3306/sentinel_security?charset=utf8mb4'
    ollama_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen2.5:3b'
    ollama_timeout: float = 180
    frontend_origins: str = 'http://127.0.0.1:5173,http://localhost:5173'
    session_hours: int = 12
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[1] / '.env', extra='ignore')

settings = Settings()
