from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USERNAME: str = "root"
    DB_PASSWORD: str = ""
    DB_DATABASE: str = "restaurant_app"
    
    # API
    API_TITLE: str = "Reelish Database API"
    API_VERSION: str = "2.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    # Debug
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()