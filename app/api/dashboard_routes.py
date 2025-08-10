"""
Dashboard API routes for the GitHub-Devin integration.
"""

from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, Depends

from ..models.dashboard_models import (
    DashboardStats, IssueWithAnalysis, RepositoryStats, DashboardFilter,
    ConfidenceLevel, ComplexityLevel
)
from ..models.devin_models import DevinSessionStatus
from ..services.session_service import SessionService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Dependency
def get_session_service() -> SessionService:
    return SessionService()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session_service: SessionService = Depends(get_session_service)
):
    """Get overall dashboard statistics."""
    try:
        stats = await session_service.get_dashboard_stats()
        
        logger.info("Retrieved dashboard stats", 
                   total_issues=stats.total_issues,
                   analyzed_issues=stats.analyzed_issues,
                   active_sessions=stats.active_sessions)
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get dashboard stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard statistics")


@router.get("/issues", response_model=List[IssueWithAnalysis])
async def get_dashboard_issues(
    repository: Optional[str] = Query(None, description="Filter by repository"),
    confidence_level: Optional[ConfidenceLevel] = Query(None, description="Filter by confidence level"),
    complexity_level: Optional[ComplexityLevel] = Query(None, description="Filter by complexity level"),
    automation_ready_only: bool = Query(False, description="Show only automation-ready issues"),
    sort_by: str = Query("priority", description="Sort by: priority, confidence, created, updated"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    limit: int = Query(50, le=200, description="Maximum number of issues to return"),
    session_service: SessionService = Depends(get_session_service)
):
    """Get issues with analysis for dashboard display."""
    try:
        # Get issues from session service
        issues = await session_service.get_dashboard_issues(
            repository_name=repository,
            limit=limit
        )
        
        # Apply filters
        filtered_issues = []
        for issue in issues:
            # Filter by confidence level
            if confidence_level and issue.analysis:
                if issue.analysis.confidence_level != confidence_level:
                    continue
            
            # Filter by complexity level
            if complexity_level and issue.analysis:
                if issue.analysis.complexity_level != complexity_level:
                    continue
            
            # Filter by automation readiness
            if automation_ready_only and not issue.is_automation_ready:
                continue
            
            filtered_issues.append(issue)
        
        # Apply sorting
        if sort_by == "priority":
            filtered_issues.sort(key=lambda x: x.priority_score, reverse=(sort_order == "desc"))
        elif sort_by == "confidence" and filtered_issues:
            filtered_issues.sort(
                key=lambda x: x.analysis.overall_confidence if x.analysis else 0.0,
                reverse=(sort_order == "desc")
            )
        elif sort_by == "created":
            filtered_issues.sort(
                key=lambda x: x.issue.created_at,
                reverse=(sort_order == "desc")
            )
        elif sort_by == "updated":
            filtered_issues.sort(
                key=lambda x: x.issue.updated_at,
                reverse=(sort_order == "desc")
            )
        
        logger.info("Retrieved dashboard issues", 
                   total_count=len(issues),
                   filtered_count=len(filtered_issues),
                   repository=repository,
                   automation_ready_only=automation_ready_only)
        
        return filtered_issues
        
    except Exception as e:
        logger.error("Failed to get dashboard issues", 
                    repository=repository, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard issues")


@router.get("/issues/automation-ready", response_model=List[IssueWithAnalysis])
async def get_automation_ready_issues(
    repository: Optional[str] = Query(None, description="Filter by repository"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence score"),
    limit: int = Query(20, le=100, description="Maximum number of issues to return"),
    session_service: SessionService = Depends(get_session_service)
):
    """Get issues that are ready for automation."""
    try:
        # Get all issues
        issues = await session_service.get_dashboard_issues(
            repository_name=repository,
            limit=limit * 2  # Get more to account for filtering
        )
        
        # Filter for automation-ready issues
        automation_ready = []
        for issue in issues:
            if (issue.is_automation_ready and 
                issue.analysis and 
                issue.analysis.overall_confidence >= min_confidence):
                automation_ready.append(issue)
                
                if len(automation_ready) >= limit:
                    break
        
        # Sort by priority score
        automation_ready.sort(key=lambda x: x.priority_score, reverse=True)
        
        logger.info("Retrieved automation-ready issues", 
                   count=len(automation_ready),
                   repository=repository,
                   min_confidence=min_confidence)
        
        return automation_ready
        
    except Exception as e:
        logger.error("Failed to get automation-ready issues", 
                    repository=repository, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get automation-ready issues")


@router.get("/repositories/{repository_name}/stats", response_model=RepositoryStats)
async def get_repository_stats(
    repository_name: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Get statistics for a specific repository."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(
                status_code=400, 
                detail="Repository name must be in format 'owner/repo'"
            )
        
        # Get issues for this repository
        issues = await session_service.get_dashboard_issues(
            repository_name=repository_name,
            limit=1000  # Get all issues for stats
        )
        
        # Calculate statistics
        total_issues = len(issues)
        open_issues = len([i for i in issues if i.issue.state == 'open'])
        analyzed_issues = len([i for i in issues if i.analysis])
        automated_issues = len([i for i in issues if i.is_automation_ready])
        
        # Calculate average confidence
        confidence_scores = [
            i.analysis.overall_confidence 
            for i in issues 
            if i.analysis
        ]
        average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Get top issues by priority
        top_issues = sorted(issues, key=lambda x: x.priority_score, reverse=True)[:10]
        
        # Create repository stats
        stats = RepositoryStats(
            repository_name=repository_name,
            total_issues=total_issues,
            open_issues=open_issues,
            analyzed_issues=analyzed_issues,
            automated_issues=automated_issues,
            average_confidence=average_confidence,
            automation_success_rate=0.0,  # Would need session tracking
            recent_sessions=[],  # Would need session tracking
            top_issues=top_issues,
            primary_language=None,  # Could be fetched from GitHub API
            technologies=[]
        )
        
        logger.info("Retrieved repository stats", 
                   repository=repository_name,
                   total_issues=total_issues,
                   analyzed_issues=analyzed_issues)
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get repository stats", 
                    repository=repository_name, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get repository statistics")


@router.get("/summary")
async def get_dashboard_summary(
    session_service: SessionService = Depends(get_session_service)
):
    """Get a summary of dashboard data for quick overview."""
    try:
        # Get dashboard stats
        stats = await session_service.get_dashboard_stats()
        
        # Get top automation-ready issues
        automation_ready = await get_automation_ready_issues(limit=5, session_service=session_service)
        
        # Create summary
        summary = {
            "overview": {
                "total_issues": stats.total_issues,
                "analyzed_issues": stats.analyzed_issues,
                "high_confidence_issues": stats.high_confidence_issues,
                "automation_ready_issues": len(automation_ready),
                "active_sessions": stats.active_sessions,
                "success_rate": stats.automation_success_rate
            },
            "complexity_distribution": {
                "low": stats.low_complexity_issues,
                "medium": stats.medium_complexity_issues,
                "high": stats.high_complexity_issues
            },
            "recent_activity": {
                "issues_analyzed_today": stats.issues_analyzed_today,
                "sessions_started_today": stats.sessions_started_today,
                "sessions_completed_today": stats.sessions_completed_today
            },
            "top_automation_candidates": [
                {
                    "repository": issue.issue.repository.full_name if issue.issue.repository else "unknown",
                    "issue_number": issue.issue.number,
                    "title": issue.issue.title,
                    "confidence_score": issue.analysis.overall_confidence if issue.analysis else 0.0,
                    "priority_score": issue.priority_score,
                    "url": issue.issue.html_url
                }
                for issue in automation_ready
            ],
            "timestamp": stats.last_updated
        }
        
        logger.info("Generated dashboard summary", 
                   total_issues=stats.total_issues,
                   automation_ready=len(automation_ready))
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get dashboard summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard summary")


@router.post("/refresh")
async def refresh_dashboard_data(
    session_service: SessionService = Depends(get_session_service)
):
    """Refresh dashboard data by re-analyzing issues."""
    try:
        # This would trigger a background task to refresh all issue analyses
        # For now, just return a success message
        
        logger.info("Dashboard refresh requested")
        
        return {
            "status": "success",
            "message": "Dashboard refresh initiated",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error("Failed to refresh dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to refresh dashboard data")
