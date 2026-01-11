"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field, computed_field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Linux Firewall & Network Manager"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./firewall_ui.db"
    
    # CORS - stored as comma-separated string, accessed as list via property
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS"
    )
    
    @computed_field
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(',') if origin.strip()]
    
    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    
    # Nginx Proxy Manager
    NPM_URL: str = ""
    NPM_EMAIL: str = ""
    NPM_PASSWORD: str = ""
    
    # Docker
    DOCKER_SOCKET: str = "/var/run/docker.sock"
    
    # Redis (for background tasks)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API Port
    API_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        populate_by_name = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
