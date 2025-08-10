"""
Pydantic models for GitHub API data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user model."""
    login: str
    id: int
    avatar_url: str
    html_url: str
    type: str = "User"


class GitHubLabel(BaseModel):
    """GitHub issue label model."""
    id: int
    name: str
    color: str
    description: Optional[str] = None


class GitHubMilestone(BaseModel):
    """GitHub milestone model."""
    id: int
    number: int
    title: str
    description: Optional[str] = None
    state: str
    created_at: datetime
    updated_at: datetime
    due_on: Optional[datetime] = None


class GitHubRepository(BaseModel):
    """GitHub repository model."""
    id: int
    name: str
    full_name: str
    owner: GitHubUser
    html_url: str
    description: Optional[str] = None
    private: bool = False
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0


class GitHubIssue(BaseModel):
    """GitHub issue model with all relevant fields."""
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str  # "open" or "closed"
    user: GitHubUser
    assignee: Optional[GitHubUser] = None
    assignees: List[GitHubUser] = []
    labels: List[GitHubLabel] = []
    milestone: Optional[GitHubMilestone] = None
    comments: int = 0
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    html_url: str
    repository: Optional[GitHubRepository] = None
    
    # Additional computed fields
    is_pull_request: bool = False
    complexity_score: Optional[float] = None
    confidence_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GitHubIssueComment(BaseModel):
    """GitHub issue comment model."""
    id: int
    body: str
    user: GitHubUser
    created_at: datetime
    updated_at: datetime
    html_url: str


class GitHubIssueFilter(BaseModel):
    """Filter parameters for GitHub issues."""
    state: str = "open"  # "open", "closed", "all"
    labels: Optional[List[str]] = None
    assignee: Optional[str] = None
    creator: Optional[str] = None
    mentioned: Optional[str] = None
    milestone: Optional[str] = None
    since: Optional[datetime] = None
    sort: str = "created"  # "created", "updated", "comments"
    direction: str = "desc"  # "asc", "desc"
    per_page: int = Field(default=30, le=100)
    page: int = Field(default=1, ge=1)


class GitHubIssueResponse(BaseModel):
    """Response model for GitHub issues API."""
    issues: List[GitHubIssue]
    total_count: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
