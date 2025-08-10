"""
GitHub API routes for the dashboard.
"""

from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ..models.github_models import (
    GitHubIssue, GitHubIssueResponse, GitHubIssueFilter, 
    GitHubRepository, GitHubIssueComment
)
from ..services.github_service import GitHubService
from ..config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()

# Dependency to get GitHub service
def get_github_service() -> GitHubService:
    return GitHubService()


class IssueAnalysisRequest(BaseModel):
    """Request to analyze a specific issue."""
    repository_name: str
    issue_number: int


@router.get("/repositories", response_model=List[str])
async def list_repositories():
    """Get list of configured repositories."""
    return settings.github_repositories


@router.get("/repositories/{repository_name}/info", response_model=GitHubRepository)
async def get_repository_info(
    repository_name: str,
    github_service: GitHubService = Depends(get_github_service)
):
    """Get information about a specific repository."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(status_code=400, detail="Repository name must be in format 'owner/repo'")
        
        repo_info = github_service.get_repository_info(repository_name)
        return repo_info
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get repository info", 
                    repository=repository_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch repository information")


@router.get("/issues", response_model=List[GitHubIssue])
async def get_all_issues(
    state: str = Query("open", description="Issue state: open, closed, all"),
    labels: Optional[str] = Query(None, description="Comma-separated list of labels"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    sort: str = Query("created", description="Sort by: created, updated, comments"),
    direction: str = Query("desc", description="Sort direction: asc, desc"),
    per_page: int = Query(30, le=100, description="Number of issues per page"),
    page: int = Query(1, ge=1, description="Page number"),
    github_service: GitHubService = Depends(get_github_service)
):
    """Get issues from all configured repositories."""
    try:
        # Create filter object
        filters = GitHubIssueFilter(
            state=state,
            labels=labels.split(",") if labels else None,
            assignee=assignee,
            sort=sort,
            direction=direction,
            per_page=per_page,
            page=page
        )
        
        # Get issues from all repositories
        issues = await github_service.get_all_issues(filters)
        
        logger.info("Retrieved all issues", 
                   count=len(issues),
                   state=state,
                   page=page)
        
        return issues
        
    except Exception as e:
        logger.error("Failed to get all issues", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch issues")


@router.get("/repositories/{repository_name}/issues", response_model=GitHubIssueResponse)
async def get_repository_issues(
    repository_name: str,
    state: str = Query("open", description="Issue state: open, closed, all"),
    labels: Optional[str] = Query(None, description="Comma-separated list of labels"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    sort: str = Query("created", description="Sort by: created, updated, comments"),
    direction: str = Query("desc", description="Sort direction: asc, desc"),
    per_page: int = Query(30, le=100, description="Number of issues per page"),
    page: int = Query(1, ge=1, description="Page number"),
    github_service: GitHubService = Depends(get_github_service)
):
    """Get issues from a specific repository."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(status_code=400, detail="Repository name must be in format 'owner/repo'")
        
        # Create filter object
        filters = GitHubIssueFilter(
            state=state,
            labels=labels.split(",") if labels else None,
            assignee=assignee,
            sort=sort,
            direction=direction,
            per_page=per_page,
            page=page
        )
        
        # Get issues from repository
        response = await github_service.get_issues(repository_name, filters)
        
        logger.info("Retrieved repository issues", 
                   repository=repository_name,
                   count=len(response.issues),
                   state=state,
                   page=page)
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get repository issues", 
                    repository=repository_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch repository issues")


@router.get("/repositories/{repository_name}/issues/{issue_number}", response_model=GitHubIssue)
async def get_issue(
    repository_name: str,
    issue_number: int,
    github_service: GitHubService = Depends(get_github_service)
):
    """Get a specific issue by number."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(status_code=400, detail="Repository name must be in format 'owner/repo'")
        
        # Validate issue number
        if issue_number <= 0:
            raise HTTPException(status_code=400, detail="Issue number must be positive")
        
        issue = await github_service.get_issue_by_number(repository_name, issue_number)
        
        logger.info("Retrieved issue", 
                   repository=repository_name,
                   issue_number=issue_number,
                   issue_title=issue.title)
        
        return issue
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get issue", 
                    repository=repository_name,
                    issue_number=issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch issue")


@router.get("/repositories/{repository_name}/issues/{issue_number}/comments", 
           response_model=List[GitHubIssueComment])
async def get_issue_comments(
    repository_name: str,
    issue_number: int,
    github_service: GitHubService = Depends(get_github_service)
):
    """Get comments for a specific issue."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(status_code=400, detail="Repository name must be in format 'owner/repo'")
        
        # Validate issue number
        if issue_number <= 0:
            raise HTTPException(status_code=400, detail="Issue number must be positive")
        
        comments = await github_service.get_issue_comments(repository_name, issue_number)
        
        logger.info("Retrieved issue comments", 
                   repository=repository_name,
                   issue_number=issue_number,
                   comment_count=len(comments))
        
        return comments
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get issue comments", 
                    repository=repository_name,
                    issue_number=issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch issue comments")


@router.get("/stats")
async def get_github_stats(
    github_service: GitHubService = Depends(get_github_service)
):
    """Get GitHub statistics across all repositories."""
    try:
        stats = {}
        
        for repo_name in settings.github_repositories:
            try:
                # Get repository info
                repo_info = github_service.get_repository_info(repo_name)
                
                # Get open issues count
                open_issues_response = await github_service.get_issues(
                    repo_name, 
                    GitHubIssueFilter(state="open", per_page=1)
                )
                
                stats[repo_name] = {
                    "name": repo_info.name,
                    "full_name": repo_info.full_name,
                    "description": repo_info.description,
                    "language": repo_info.language,
                    "stars": repo_info.stargazers_count,
                    "forks": repo_info.forks_count,
                    "open_issues": open_issues_response.total_count,
                    "url": repo_info.html_url
                }
                
            except Exception as e:
                logger.warning("Failed to get stats for repository", 
                              repository=repo_name, 
                              error=str(e))
                stats[repo_name] = {"error": str(e)}
        
        return {
            "repositories": stats,
            "total_repositories": len(settings.github_repositories),
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error("Failed to get GitHub stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch GitHub statistics")
