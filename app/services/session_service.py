"""
Session management service for coordinating GitHub issues and Devin sessions.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import structlog

from ..models.github_models import GitHubIssue
from ..models.devin_models import (
    DevinSession, DevinSessionStatus, DevinSessionType, DevinSessionSummary,
    DevinScopeResult, DevinCompletionResult
)
from ..models.dashboard_models import (
    IssueWithAnalysis, SessionSummary, DashboardStats, RepositoryStats
)
from .github_service import GitHubService
from .devin_service import DevinService
from .analysis_service import AnalysisService

logger = structlog.get_logger(__name__)


class SessionService:
    """Service for managing the complete workflow of issue analysis and Devin sessions."""
    
    def __init__(self):
        """Initialize session service with dependent services."""
        self.github_service = GitHubService()
        self.devin_service = DevinService()
        self.analysis_service = AnalysisService()
        
        # In-memory storage for session tracking
        # In production, this would be backed by a database
        self.active_sessions: Dict[str, DevinSession] = {}
        self.session_results: Dict[str, Dict] = {}
        self.issue_analyses: Dict[str, IssueWithAnalysis] = {}

        # Cache for dashboard stats to reduce Devin API calls
        self._stats_cache: Optional[DashboardStats] = None
        self._stats_cache_time: Optional[datetime] = None
        self._stats_cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
    
    async def get_dashboard_issues(
        self, 
        repository_name: Optional[str] = None,
        limit: int = 50
    ) -> List[IssueWithAnalysis]:
        """
        Get issues with analysis for dashboard display.
        
        Args:
            repository_name: Specific repository or None for all
            limit: Maximum number of issues to return
            
        Returns:
            List of issues with analysis data
        """
        try:
            # Fetch issues from GitHub
            if repository_name:
                github_response = await self.github_service.get_issues(repository_name)
                issues = github_response.issues
            else:
                issues = await self.github_service.get_all_issues()
            
            # Limit results
            issues = issues[:limit]
            
            # Create dashboard objects (without automatic analysis generation)
            dashboard_issues = []
            for issue in issues:
                # Check if we have cached analysis
                cache_key = f"{issue.repository.full_name if issue.repository else 'unknown'}#{issue.number}"

                if cache_key in self.issue_analyses:
                    issue_with_analysis = self.issue_analyses[cache_key]
                    # Update the issue data (in case it changed)
                    issue_with_analysis.issue = issue
                else:
                    # Create issue without analysis (clean state)
                    from ..models.dashboard_models import IssueWithAnalysis
                    issue_with_analysis = IssueWithAnalysis(
                        issue=issue,
                        analysis=None,
                        active_sessions=[]
                    )

                # Add active sessions
                issue_with_analysis.active_sessions = await self._get_active_sessions_for_issue(issue)

                dashboard_issues.append(issue_with_analysis)
            
            # Sort by priority score
            dashboard_issues.sort(key=lambda x: x.priority_score, reverse=True)
            
            logger.info("Retrieved dashboard issues", 
                       count=len(dashboard_issues),
                       repository=repository_name)
            
            return dashboard_issues
            
        except Exception as e:
            logger.error("Failed to get dashboard issues", 
                        repository=repository_name, 
                        error=str(e))
            raise
    
    async def trigger_issue_scoping(
        self, 
        repository_name: str, 
        issue_number: int
    ) -> DevinScopeResult:
        """
        Trigger a Devin session to scope a GitHub issue.
        
        Args:
            repository_name: Repository name (owner/repo)
            issue_number: Issue number
            
        Returns:
            DevinScopeResult with scoping analysis
        """
        try:
            # Get the issue from GitHub
            issue = await self.github_service.get_issue_by_number(repository_name, issue_number)
            
            logger.info("Triggering issue scoping", 
                       repository=repository_name,
                       issue_number=issue_number,
                       issue_title=issue.title)
            
            # Trigger Devin scoping session
            scope_result = await self.devin_service.scope_github_issue(issue)
            
            # Store result for future reference
            result_key = f"{repository_name}#{issue_number}#scope"
            self.session_results[result_key] = {
                'type': 'scope',
                'result': scope_result,
                'timestamp': datetime.now()
            }
            
            # Update issue analysis with scoping results
            cache_key = f"{repository_name}#{issue_number}"
            if cache_key in self.issue_analyses:
                issue_analysis = self.issue_analyses[cache_key]
                if issue_analysis.analysis:
                    issue_analysis.analysis.overall_confidence = scope_result.confidence_score
                    issue_analysis.analysis.complexity_level = scope_result.complexity_estimate
            
            logger.info("Issue scoping completed", 
                       session_id=scope_result.session_id,
                       confidence_score=scope_result.confidence_score,
                       complexity=scope_result.complexity_estimate)
            
            return scope_result
            
        except Exception as e:
            logger.error("Failed to trigger issue scoping", 
                        repository=repository_name,
                        issue_number=issue_number,
                        error=str(e))
            raise
    
    async def trigger_issue_completion(
        self, 
        repository_name: str, 
        issue_number: int,
        use_existing_scope: bool = True
    ) -> DevinCompletionResult:
        """
        Trigger a Devin session to complete a GitHub issue.
        
        Args:
            repository_name: Repository name (owner/repo)
            issue_number: Issue number
            use_existing_scope: Whether to use existing scope results
            
        Returns:
            DevinCompletionResult with completion status
        """
        try:
            # Get the issue from GitHub
            issue = await self.github_service.get_issue_by_number(repository_name, issue_number)
            
            # Get or create scope results
            scope_result = None
            if use_existing_scope:
                result_key = f"{repository_name}#{issue_number}#scope"
                if result_key in self.session_results:
                    scope_result = self.session_results[result_key]['result']
            
            if not scope_result:
                logger.info("No existing scope found, creating new scope", 
                           repository=repository_name,
                           issue_number=issue_number)
                scope_result = await self.trigger_issue_scoping(repository_name, issue_number)
            
            logger.info("Triggering issue completion", 
                       repository=repository_name,
                       issue_number=issue_number,
                       confidence_score=scope_result.confidence_score)
            
            # Trigger Devin completion session
            completion_result = await self.devin_service.complete_github_issue(issue, scope_result)
            
            # Store result for future reference
            result_key = f"{repository_name}#{issue_number}#completion"
            self.session_results[result_key] = {
                'type': 'completion',
                'result': completion_result,
                'timestamp': datetime.now()
            }
            
            logger.info("Issue completion started", 
                       session_id=completion_result.session_id,
                       status=completion_result.status)
            
            return completion_result
            
        except Exception as e:
            logger.error("Failed to trigger issue completion", 
                        repository=repository_name,
                        issue_number=issue_number,
                        error=str(e))
            raise
    
    async def get_session_status(self, session_id: str) -> Optional[DevinSession]:
        """Get current status of a Devin session."""
        try:
            # Check cache first
            cached_session = self.devin_service.get_cached_session(session_id)
            if cached_session:
                return cached_session
            
            # Get fresh details from API
            details = await self.devin_service.get_session_details(session_id)
            
            # Convert to session object
            session = DevinSession(
                session_id=details.session_id,
                status=details.status,
                session_type=DevinSessionType.GENERAL,  # Would need to be stored
                created_at=details.created_at,
                updated_at=details.updated_at,
                completed_at=details.completed_at,
                prompt=details.prompt,
                output=details.output,
                error_message=details.error_message,
                session_url=details.url
            )
            
            return session
            
        except Exception as e:
            logger.error("Failed to get session status", 
                        session_id=session_id, 
                        error=str(e))
            return None
    
    async def get_dashboard_stats(self) -> DashboardStats:
        """Get overall dashboard statistics by calling Devin Sessions endpoint directly."""
        try:
            # Get all issues across repositories
            all_issues = await self.github_service.get_all_issues()

            # Always call Devin API directly for fresh session data
            session_summaries = await self.devin_service.list_sessions()
            logger.info("Successfully retrieved Devin sessions", count=len(session_summaries))
            
            # Calculate statistics
            total_issues = len(all_issues)
            open_issues = len([issue for issue in all_issues if issue.state == 'open'])
            analyzed_issues = len(self.issue_analyses)
            
            # Count high confidence issues
            high_confidence_issues = 0
            automated_issues = 0
            complexity_counts = {'low': 0, 'medium': 0, 'high': 0}
            
            for issue_analysis in self.issue_analyses.values():
                if issue_analysis.analysis:
                    if issue_analysis.analysis.confidence_level.value == 'high':
                        high_confidence_issues += 1
                    if issue_analysis.analysis.automation_suitable:
                        automated_issues += 1
                    
                    complexity = issue_analysis.analysis.complexity_level.value
                    if complexity in complexity_counts:
                        complexity_counts[complexity] += 1
            
            # Session statistics
            total_sessions = len(session_summaries)
            active_sessions = len([s for s in session_summaries if s.status == DevinSessionStatus.RUNNING])
            completed_sessions = len([s for s in session_summaries if s.status == DevinSessionStatus.COMPLETED])
            failed_sessions = len([s for s in session_summaries if s.status == DevinSessionStatus.FAILED])
            
            # Calculate success rate
            automation_success_rate = 0.0
            if completed_sessions + failed_sessions > 0:
                automation_success_rate = completed_sessions / (completed_sessions + failed_sessions)
            
            # Calculate average confidence
            confidence_scores = [
                ia.analysis.overall_confidence 
                for ia in self.issue_analyses.values() 
                if ia.analysis
            ]
            average_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Today's activity (simplified - would use proper date filtering in production)
            today = datetime.now().date()
            issues_analyzed_today = len([
                ia for ia in self.issue_analyses.values() 
                if ia.analysis and ia.analysis.analyzed_at.date() == today
            ])
            
            sessions_today = [
                s for s in session_summaries 
                if s.created_at.date() == today
            ]
            sessions_started_today = len(sessions_today)
            sessions_completed_today = len([
                s for s in sessions_today 
                if s.status == DevinSessionStatus.COMPLETED
            ])
            
            stats = DashboardStats(
                total_issues=total_issues,
                open_issues=open_issues,
                analyzed_issues=analyzed_issues,
                high_confidence_issues=high_confidence_issues,
                automated_issues=automated_issues,
                total_sessions=total_sessions,
                active_sessions=active_sessions,
                completed_sessions=completed_sessions,
                failed_sessions=failed_sessions,
                average_confidence_score=average_confidence_score,
                automation_success_rate=automation_success_rate,
                issues_analyzed_today=issues_analyzed_today,
                sessions_started_today=sessions_started_today,
                sessions_completed_today=sessions_completed_today,
                low_complexity_issues=complexity_counts['low'],
                medium_complexity_issues=complexity_counts['medium'],
                high_complexity_issues=complexity_counts['high']
            )
            
            logger.info("Generated dashboard stats from fresh Devin API data",
                       total_issues=total_issues,
                       analyzed_issues=analyzed_issues,
                       active_sessions=active_sessions)

            return stats
            
        except Exception as e:
            logger.error("Failed to get dashboard stats", error=str(e))
            # Return empty stats on error
            return DashboardStats()
    
    async def _get_active_sessions_for_issue(self, issue: GitHubIssue) -> List[SessionSummary]:
        """Get active sessions for a specific issue."""
        # This would query the database for sessions related to this issue
        # For now, return empty list
        return []

    def clear_all_scoping_data(self) -> Dict[str, int]:
        """Clear all cached scoping data and return counts of cleared items."""
        try:
            # Count items before clearing
            analyses_count = len(self.issue_analyses)
            results_count = len(self.session_results)
            sessions_count = len(self.active_sessions)

            # Clear all cached data
            self.issue_analyses.clear()
            self.session_results.clear()
            self.active_sessions.clear()

            logger.info("Cleared all scoping data",
                       analyses_cleared=analyses_count,
                       results_cleared=results_count,
                       sessions_cleared=sessions_count)

            return {
                "issue_analyses": analyses_count,
                "session_results": results_count,
                "active_sessions": sessions_count
            }

        except Exception as e:
            logger.error("Failed to clear scoping data", error=str(e))
            raise

    async def generate_issue_analysis(self, repository_name: str, issue_number: int) -> bool:
        """Generate analysis for a specific issue and cache it."""
        try:
            # Get the issue from GitHub
            issue = await self.github_service.get_issue_by_number(repository_name, issue_number)

            # Generate analysis
            issue_with_analysis = self.analysis_service.create_issue_with_analysis(issue)

            # Cache the analysis
            cache_key = f"{repository_name}#{issue_number}"
            self.issue_analyses[cache_key] = issue_with_analysis

            logger.info("Generated issue analysis",
                       repository=repository_name,
                       issue_number=issue_number,
                       confidence=issue_with_analysis.analysis.overall_confidence if issue_with_analysis.analysis else None)

            return True

        except Exception as e:
            logger.error("Failed to generate issue analysis",
                        repository=repository_name,
                        issue_number=issue_number,
                        error=str(e))
            return False
