"""
Pydantic models for dashboard data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .github_models import GitHubIssue
from .devin_models import DevinSessionSummary, DevinSessionStatus, DevinSessionType


class ComplexityLevel(str, Enum):
    """Issue complexity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence levels for automation."""
    LOW = "low"          # 0.0 - 0.4
    MEDIUM = "medium"    # 0.4 - 0.7
    HIGH = "high"        # 0.7 - 1.0


class IssueAnalysis(BaseModel):
    """Analysis results for a GitHub issue."""
    issue_id: int
    issue_number: int
    repository_name: str
    
    # Confidence scoring
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    
    # Complexity analysis
    complexity_score: float = Field(..., ge=0.0, le=1.0)
    complexity_level: ComplexityLevel
    estimated_hours: Optional[float] = None
    
    # Detailed scoring factors
    requirements_clarity: float = Field(..., ge=0.0, le=1.0)
    technical_feasibility: float = Field(..., ge=0.0, le=1.0)
    scope_completeness: float = Field(..., ge=0.0, le=1.0)
    context_availability: float = Field(..., ge=0.0, le=1.0)
    
    # Analysis details
    key_factors: List[str] = []
    potential_challenges: List[str] = []
    recommended_action: str
    automation_suitable: bool
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    analysis_version: str = "1.0"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionSummary(BaseModel):
    """Summary of a Devin session for dashboard display."""
    session_id: str
    session_type: DevinSessionType
    status: DevinSessionStatus
    
    # Issue information
    repository_name: Optional[str] = None
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    
    # Timing
    created_at: datetime
    updated_at: datetime
    duration_minutes: Optional[float] = None
    
    # Progress and results
    progress_percentage: Optional[float] = None
    confidence_score: Optional[float] = None
    success_rate: Optional[float] = None
    
    # URLs
    session_url: str
    github_issue_url: Optional[str] = None


class DashboardStats(BaseModel):
    """Overall statistics for the dashboard."""
    
    # Issue statistics
    total_issues: int = 0
    open_issues: int = 0
    analyzed_issues: int = 0
    high_confidence_issues: int = 0
    automated_issues: int = 0
    
    # Session statistics
    total_sessions: int = 0
    active_sessions: int = 0
    completed_sessions: int = 0
    failed_sessions: int = 0
    
    # Success metrics
    average_confidence_score: float = 0.0
    automation_success_rate: float = 0.0
    average_completion_time: float = 0.0  # in hours
    
    # Recent activity
    issues_analyzed_today: int = 0
    sessions_started_today: int = 0
    sessions_completed_today: int = 0
    
    # Complexity distribution
    low_complexity_issues: int = 0
    medium_complexity_issues: int = 0
    high_complexity_issues: int = 0
    
    # Time-based metrics
    last_updated: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IssueWithAnalysis(BaseModel):
    """GitHub issue combined with analysis results."""
    issue: GitHubIssue
    analysis: Optional[IssueAnalysis] = None
    active_sessions: List[SessionSummary] = []
    
    @property
    def is_automation_ready(self) -> bool:
        """Check if issue is ready for automation."""
        if not self.analysis:
            return False
        return (
            self.analysis.automation_suitable and 
            self.analysis.overall_confidence >= 0.7
        )
    
    @property
    def priority_score(self) -> float:
        """Calculate priority score for dashboard sorting."""
        base_score = 0.0
        
        if self.analysis:
            # Higher confidence = higher priority
            base_score += self.analysis.overall_confidence * 0.4
            
            # Lower complexity = higher priority (easier to automate)
            complexity_bonus = {
                ComplexityLevel.LOW: 0.3,
                ComplexityLevel.MEDIUM: 0.2,
                ComplexityLevel.HIGH: 0.1,
                ComplexityLevel.UNKNOWN: 0.0
            }
            base_score += complexity_bonus.get(self.analysis.complexity_level, 0.0)
        
        # Recent issues get slight priority boost
        days_old = (datetime.now() - self.issue.created_at).days
        if days_old < 7:
            base_score += 0.1
        elif days_old < 30:
            base_score += 0.05
        
        # Issues with labels get slight boost
        if self.issue.labels:
            base_score += 0.05
        
        return min(base_score, 1.0)


class RepositoryStats(BaseModel):
    """Statistics for a specific repository."""
    repository_name: str
    
    # Issue counts
    total_issues: int = 0
    open_issues: int = 0
    analyzed_issues: int = 0
    automated_issues: int = 0
    
    # Success metrics
    average_confidence: float = 0.0
    automation_success_rate: float = 0.0
    
    # Recent activity
    recent_sessions: List[SessionSummary] = []
    top_issues: List[IssueWithAnalysis] = []
    
    # Language and technology info
    primary_language: Optional[str] = None
    technologies: List[str] = []
    
    last_updated: datetime = Field(default_factory=datetime.now)


class DashboardFilter(BaseModel):
    """Filter options for dashboard views."""
    repositories: Optional[List[str]] = None
    confidence_levels: Optional[List[ConfidenceLevel]] = None
    complexity_levels: Optional[List[ComplexityLevel]] = None
    session_statuses: Optional[List[DevinSessionStatus]] = None
    date_range_days: Optional[int] = 30
    automation_ready_only: bool = False
    sort_by: str = "priority"  # "priority", "confidence", "created", "updated"
    sort_order: str = "desc"   # "asc", "desc"
    limit: int = Field(default=50, le=200)
