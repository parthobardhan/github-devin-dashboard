"""
Database setup and models for the GitHub-Devin Dashboard application.
"""

import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# Create SQLAlchemy base
Base = declarative_base()


class DevinSessionDB(Base):
    """Database model for storing Devin session information."""
    __tablename__ = "devin_sessions"
    
    # Primary key
    session_id = Column(String(255), primary_key=True)
    
    # Session metadata
    status = Column(String(50), nullable=False, default="pending")
    session_type = Column(String(50), nullable=False, default="general")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Request information
    prompt = Column(Text, nullable=False)
    repository_name = Column(String(255), nullable=True)
    issue_number = Column(Integer, nullable=True)
    issue_title = Column(String(500), nullable=True)
    tags = Column(SQLiteJSON, nullable=True)  # Store as JSON array
    
    # Results and analysis
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # URLs and links
    session_url = Column(String(500), nullable=False)
    github_issue_url = Column(String(500), nullable=True)
    
    # Timing information
    duration_minutes = Column(Float, nullable=True)
    estimated_completion_time = Column(Integer, nullable=True)


class ScopingResultDB(Base):
    """Database model for storing scoping analysis results."""
    __tablename__ = "scoping_results"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Issue information
    repository_name = Column(String(255), nullable=False, index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    issue_title = Column(String(500), nullable=True)
    
    # Scoping results
    confidence_score = Column(Float, nullable=False)
    complexity_estimate = Column(String(50), nullable=False)  # "low", "medium", "high"
    estimated_hours = Column(Float, nullable=True)
    
    # Analysis details
    requirements_clarity = Column(Float, nullable=False)
    technical_feasibility = Column(Float, nullable=False)
    scope_completeness = Column(Float, nullable=False)
    
    # Recommendations and analysis (stored as JSON)
    recommended_approach = Column(Text, nullable=True)
    potential_challenges = Column(SQLiteJSON, nullable=True)  # JSON array
    required_knowledge = Column(SQLiteJSON, nullable=True)  # JSON array
    dependencies = Column(SQLiteJSON, nullable=True)  # JSON array
    action_plan = Column(SQLiteJSON, nullable=True)  # JSON array
    acceptance_criteria = Column(SQLiteJSON, nullable=True)  # JSON array
    
    # File paths and structure analysis
    relevant_files = Column(SQLiteJSON, nullable=True)  # JSON array of file paths
    file_analysis = Column(Text, nullable=True)  # Detailed file structure analysis
    
    # Session metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    analysis_duration_minutes = Column(Float, nullable=True)


class RepositoryFileDB(Base):
    """Database model for storing repository file structure and analysis."""
    __tablename__ = "repository_files"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Repository information
    repository_name = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False, index=True)
    file_type = Column(String(50), nullable=True)  # "source", "config", "test", etc.
    
    # File metadata
    file_size = Column(Integer, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    language = Column(String(50), nullable=True)
    
    # Analysis results
    complexity_score = Column(Float, nullable=True)
    importance_score = Column(Float, nullable=True)  # How important this file is for issues
    description = Column(Text, nullable=True)  # AI-generated description of file purpose
    
    # Relationships to issues
    related_issues = Column(SQLiteJSON, nullable=True)  # JSON array of issue numbers
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PreviousScopingDB(Base):
    """Database model for storing summaries of previous scoping sessions."""
    __tablename__ = "previous_scoping"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference information
    repository_name = Column(String(255), nullable=False, index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Summary information
    summary = Column(Text, nullable=False)  # Concise summary of scoping results
    key_insights = Column(SQLiteJSON, nullable=True)  # JSON array of key insights
    implementation_approach = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    
    # Success metrics
    was_successful = Column(Boolean, nullable=True)
    actual_completion_time = Column(Float, nullable=True)  # Hours
    accuracy_score = Column(Float, nullable=True)  # How accurate the scoping was
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database connection and session management
class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return
        
        try:
            # Create engine
            self.engine = create_engine(
                settings.database_url,
                echo=settings.app_debug,  # Log SQL queries in debug mode
                pool_pre_ping=True,  # Verify connections before use
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.info("Database initialized successfully", 
                       database_url=settings.database_url)
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    def get_session(self) -> Session:
        """Get a database session."""
        if not self._initialized:
            self.initialize()
        
        return self.SessionLocal()
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Session:
    """Dependency function to get database session for FastAPI."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()
