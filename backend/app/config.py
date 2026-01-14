from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # MongoDB Settings
    MONGO_URL: str
    DB_NAME: str = "mvp_db"
    
    # AI Services
    DEEPGRAM_API_KEY: str
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str
    
    # RAG Settings
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 250
    VECTOR_INDEX_NAME: str = "vector_index"
    DOCUMENT_CHUNKS_COLLECTION: str = "document_chunks"
    
    # Groq Settings
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    
    # Transport
    TRANSPORT: str = "single"  # single or dual
    
    # Hardcoded for MVP (no auth)
    TENANT_ID: str = "mvp_tenant"
    USER_ID: str = "mvp_user"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

