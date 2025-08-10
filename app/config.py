"""
Configuration management for the GitHub-Devin Dashboard application.
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GitHub Configuration
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_repos: str = Field(..., env="GITHUB_REPOS")
    
    # Devin API Configuration
    devin_api_key: str = Field(..., env="DEVIN_API_KEY")
    devin_api_base_url: str = Field("https://api.devin.ai/v1", env="DEVIN_API_BASE_URL")
    
    # Application Configuration
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8000, env="APP_PORT")
    app_debug: bool = Field(False, env="APP_DEBUG")
    app_secret_key: str = Field(..., env="APP_SECRET_KEY")
    
    # Database Configuration
    database_url: str = Field("sqlite:///./github_devin_dashboard.db", env="DATABASE_URL")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # Dashboard Configuration
    dashboard_title: str = Field("GitHub-Devin Integration Dashboard", env="DASHBOARD_TITLE")
    dashboard_refresh_interval: int = Field(30, env="DASHBOARD_REFRESH_INTERVAL")
    
    # Session Configuration
    session_timeout: int = Field(3600, env="SESSION_TIMEOUT")
    max_concurrent_sessions: int = Field(5, env="MAX_CONCURRENT_SESSIONS")
    
    # Issue Analysis Configuration
    confidence_threshold: float = Field(0.7, env="CONFIDENCE_THRESHOLD")
    analysis_timeout: int = Field(300, env="ANALYSIS_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def github_repositories(self) -> List[str]:
        """Parse GitHub repositories from comma-separated string."""
        return [repo.strip() for repo in self.github_repos.split(",") if repo.strip()]
    
    @property
    def devin_headers(self) -> dict:
        """Get headers for Devin API requests."""
        return {
            "Authorization": f"Bearer {self.devin_api_key}",
            "Content-Type": "application/json"
        }


# Global settings instance
settings = Settings()
