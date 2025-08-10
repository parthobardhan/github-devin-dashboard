"""
Pydantic models for Devin API data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class DevinSessionStatus(str, Enum):
    """Devin session status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    CLAIMED = "claimed"  # Added to handle status from Devin API
    FINISHED = "finished"  # Added to handle status from Devin API
    BLOCKED = "blocked"  # Added to handle status from Devin API


class DevinSessionType(str, Enum):
    """Type of Devin session."""
    SCOPE_ISSUE = "scope_issue"
    COMPLETE_ISSUE = "complete_issue"
    GENERAL = "general"


class DevinSessionRequest(BaseModel):
    """Request model for creating a Devin session."""
    prompt: str = Field(..., description="The task prompt for Devin")
    session_type: DevinSessionType = DevinSessionType.GENERAL
    repository_name: Optional[str] = None
    issue_number: Optional[int] = None
    idempotent: bool = True
    tags: List[str] = []

    # Additional context for issue-related sessions
    issue_title: Optional[str] = None
    issue_body: Optional[str] = None
    issue_labels: List[str] = []
    confidence_score: Optional[float] = None


class DevinSessionResponse(BaseModel):
    """Response model from Devin API when creating a session."""
    session_id: str
    url: str
    is_new_session: bool


class DevinSessionDetails(BaseModel):
    """Detailed information about a Devin session."""
    session_id: str
    status: DevinSessionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    url: str
    
    # Session metadata
    prompt: str
    session_type: DevinSessionType = DevinSessionType.GENERAL
    repository_name: Optional[str] = None
    issue_number: Optional[int] = None
    tags: List[str] = []
    
    # Results and outputs
    output: Optional[str] = None
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    estimated_completion_time: Optional[int] = None  # in minutes
    
    # Progress tracking
    progress_percentage: Optional[float] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DevinSession(BaseModel):
    """Complete Devin session model with all information."""
    session_id: str
    status: DevinSessionStatus
    session_type: DevinSessionType
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    
    # Request information
    prompt: str
    repository_name: Optional[str] = None
    issue_number: Optional[int] = None
    tags: List[str] = []
    
    # Results
    output: Optional[str] = None
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    
    # URLs and links
    session_url: str
    github_issue_url: Optional[str] = None
    
    # Timing information
    duration_minutes: Optional[float] = None
    estimated_completion_time: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DevinScopeResult(BaseModel):
    """Result from a Devin issue scoping session."""
    session_id: str
    issue_number: int
    repository_name: str
    
    # Scoping results
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    complexity_estimate: str  # "low", "medium", "high"
    estimated_hours: Optional[float] = None
    
    # Analysis details
    requirements_clarity: float = Field(..., ge=0.0, le=1.0)
    technical_feasibility: float = Field(..., ge=0.0, le=1.0)
    scope_completeness: float = Field(..., ge=0.0, le=1.0)
    
    # Recommendations
    recommended_approach: Optional[str] = None
    potential_challenges: List[str] = []
    required_knowledge: List[str] = []
    dependencies: List[str] = []
    
    # Action plan
    action_plan: List[str] = []
    acceptance_criteria: List[str] = []
    
    # Session metadata
    created_at: datetime
    analysis_duration_minutes: float


class DevinCompletionResult(BaseModel):
    """Result from a Devin issue completion session."""
    session_id: str
    issue_number: int
    repository_name: str
    
    # Completion results
    status: DevinSessionStatus
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    
    # Code changes
    files_modified: List[str] = []
    lines_added: int = 0
    lines_removed: int = 0
    commits_created: List[str] = []
    
    # Pull request information
    pull_request_url: Optional[str] = None
    pull_request_number: Optional[int] = None
    
    # Testing results
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    test_coverage: Optional[float] = None
    
    # Session metadata
    created_at: datetime
    completion_duration_minutes: float
    
    # Issues encountered
    errors_encountered: List[str] = []
    warnings: List[str] = []


class DevinMessage(BaseModel):
    """Message sent to or received from a Devin session."""
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    sender: Literal["user", "devin"] = "user"
    message_type: str = "text"  # "text", "code", "file", "error"


class DevinSessionSummary(BaseModel):
    """Summary information for dashboard display."""
    session_id: str
    session_type: DevinSessionType
    status: DevinSessionStatus
    repository_name: Optional[str] = None
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    created_at: datetime
    duration_minutes: Optional[float] = None
    confidence_score: Optional[float] = None
    progress_percentage: Optional[float] = None
