"""
GitHub API integration service for fetching and managing GitHub issues.
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
import structlog
from github import Github, GithubException
from github.Issue import Issue
from github.Repository import Repository

from ..config import settings
from ..models.github_models import (
    GitHubIssue, GitHubRepository, GitHubUser, GitHubLabel, 
    GitHubMilestone, GitHubIssueFilter, GitHubIssueResponse,
    GitHubIssueComment
)

logger = structlog.get_logger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    def __init__(self):
        """Initialize GitHub service with API token."""
        self.github = Github(settings.github_token)
        self.repositories = {}
        self._load_repositories()
    
    def _load_repositories(self):
        """Load and cache repository objects."""
        try:
            for repo_name in settings.github_repositories:
                repo = self.github.get_repo(repo_name)
                self.repositories[repo_name] = repo
                logger.info("Loaded repository", repo=repo_name)
        except GithubException as e:
            logger.error("Failed to load repository", error=str(e))
            raise
    
    def _convert_user(self, github_user) -> GitHubUser:
        """Convert GitHub user object to our model."""
        if not github_user:
            return None
        
        return GitHubUser(
            login=github_user.login,
            id=github_user.id,
            avatar_url=github_user.avatar_url,
            html_url=github_user.html_url,
            type=github_user.type
        )
    
    def _convert_label(self, github_label) -> GitHubLabel:
        """Convert GitHub label object to our model."""
        return GitHubLabel(
            id=github_label.id if hasattr(github_label, 'id') else 0,
            name=github_label.name,
            color=github_label.color,
            description=github_label.description
        )
    
    def _convert_milestone(self, github_milestone) -> Optional[GitHubMilestone]:
        """Convert GitHub milestone object to our model."""
        if not github_milestone:
            return None
        
        return GitHubMilestone(
            id=github_milestone.id,
            number=github_milestone.number,
            title=github_milestone.title,
            description=github_milestone.description,
            state=github_milestone.state,
            created_at=github_milestone.created_at,
            updated_at=github_milestone.updated_at,
            due_on=github_milestone.due_on
        )
    
    def _convert_repository(self, github_repo) -> GitHubRepository:
        """Convert GitHub repository object to our model."""
        return GitHubRepository(
            id=github_repo.id,
            name=github_repo.name,
            full_name=github_repo.full_name,
            owner=self._convert_user(github_repo.owner),
            html_url=github_repo.html_url,
            description=github_repo.description,
            private=github_repo.private,
            language=github_repo.language,
            stargazers_count=github_repo.stargazers_count,
            forks_count=github_repo.forks_count,
            open_issues_count=github_repo.open_issues_count
        )
    
    def _convert_issue(self, github_issue: Issue, repository: Repository = None) -> GitHubIssue:
        """Convert GitHub issue object to our model."""
        # Convert labels
        labels = [self._convert_label(label) for label in github_issue.labels]
        
        # Convert assignees
        assignees = [self._convert_user(assignee) for assignee in github_issue.assignees]
        
        # Check if it's a pull request
        is_pull_request = github_issue.pull_request is not None
        
        issue = GitHubIssue(
            id=github_issue.id,
            number=github_issue.number,
            title=github_issue.title,
            body=github_issue.body,
            state=github_issue.state,
            user=self._convert_user(github_issue.user),
            assignee=self._convert_user(github_issue.assignee),
            assignees=assignees,
            labels=labels,
            milestone=self._convert_milestone(github_issue.milestone),
            comments=github_issue.comments,
            created_at=github_issue.created_at,
            updated_at=github_issue.updated_at,
            closed_at=github_issue.closed_at,
            html_url=github_issue.html_url,
            is_pull_request=is_pull_request
        )
        
        # Add repository info if provided
        if repository:
            issue.repository = self._convert_repository(repository)
        
        return issue
    
    async def get_issues(
        self, 
        repository_name: str, 
        filters: GitHubIssueFilter = None
    ) -> GitHubIssueResponse:
        """
        Fetch issues from a specific repository.
        
        Args:
            repository_name: Name of the repository (owner/repo)
            filters: Filter parameters for issues
            
        Returns:
            GitHubIssueResponse with issues and pagination info
        """
        if not filters:
            filters = GitHubIssueFilter()
        
        try:
            repo = self.repositories.get(repository_name)
            if not repo:
                raise ValueError(f"Repository {repository_name} not found")
            
            # Build GitHub API parameters
            kwargs = {
                'state': filters.state,
                'sort': filters.sort,
                'direction': filters.direction
            }
            
            if filters.assignee:
                kwargs['assignee'] = filters.assignee
            if filters.creator:
                kwargs['creator'] = filters.creator
            if filters.mentioned:
                kwargs['mentioned'] = filters.mentioned
            if filters.milestone:
                kwargs['milestone'] = filters.milestone
            if filters.since:
                kwargs['since'] = filters.since
            if filters.labels:
                kwargs['labels'] = filters.labels
            
            # Get issues from GitHub
            github_issues = repo.get_issues(**kwargs)
            
            # Convert to paginated list
            issues_list = []
            start_idx = (filters.page - 1) * filters.per_page
            end_idx = start_idx + filters.per_page
            
            for i, github_issue in enumerate(github_issues):
                if i < start_idx:
                    continue
                if i >= end_idx:
                    break
                
                # Skip pull requests if we only want issues
                if github_issue.pull_request is not None:
                    continue
                
                issue = self._convert_issue(github_issue, repo)
                issues_list.append(issue)
            
            # Calculate pagination info
            total_count = github_issues.totalCount
            has_next = end_idx < total_count
            has_prev = filters.page > 1
            
            logger.info(
                "Fetched issues", 
                repository=repository_name,
                count=len(issues_list),
                page=filters.page,
                total=total_count
            )
            
            return GitHubIssueResponse(
                issues=issues_list,
                total_count=total_count,
                page=filters.page,
                per_page=filters.per_page,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except GithubException as e:
            logger.error("GitHub API error", error=str(e), repository=repository_name)
            raise
        except Exception as e:
            logger.error("Unexpected error fetching issues", error=str(e))
            raise
    
    async def get_all_issues(self, filters: GitHubIssueFilter = None) -> List[GitHubIssue]:
        """
        Fetch issues from all configured repositories.
        
        Args:
            filters: Filter parameters for issues
            
        Returns:
            List of all issues across repositories
        """
        all_issues = []
        
        for repo_name in settings.github_repositories:
            try:
                response = await self.get_issues(repo_name, filters)
                all_issues.extend(response.issues)
            except Exception as e:
                logger.error("Failed to fetch issues from repository", 
                           repository=repo_name, error=str(e))
                continue
        
        # Sort by updated_at descending
        all_issues.sort(key=lambda x: x.updated_at, reverse=True)
        
        return all_issues
    
    async def get_issue_by_number(self, repository_name: str, issue_number: int) -> GitHubIssue:
        """
        Get a specific issue by number.
        
        Args:
            repository_name: Name of the repository
            issue_number: Issue number
            
        Returns:
            GitHubIssue object
        """
        try:
            repo = self.repositories.get(repository_name)
            if not repo:
                raise ValueError(f"Repository {repository_name} not found")
            
            github_issue = repo.get_issue(issue_number)
            return self._convert_issue(github_issue, repo)
            
        except GithubException as e:
            logger.error("Failed to fetch issue", 
                        repository=repository_name, 
                        issue_number=issue_number, 
                        error=str(e))
            raise
    
    async def get_issue_comments(
        self, 
        repository_name: str, 
        issue_number: int
    ) -> List[GitHubIssueComment]:
        """
        Get comments for a specific issue.
        
        Args:
            repository_name: Name of the repository
            issue_number: Issue number
            
        Returns:
            List of issue comments
        """
        try:
            repo = self.repositories.get(repository_name)
            if not repo:
                raise ValueError(f"Repository {repository_name} not found")
            
            github_issue = repo.get_issue(issue_number)
            comments = []
            
            for comment in github_issue.get_comments():
                comments.append(GitHubIssueComment(
                    id=comment.id,
                    body=comment.body,
                    user=self._convert_user(comment.user),
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    html_url=comment.html_url
                ))
            
            return comments
            
        except GithubException as e:
            logger.error("Failed to fetch issue comments", 
                        repository=repository_name, 
                        issue_number=issue_number, 
                        error=str(e))
            raise
    
    def get_repository_info(self, repository_name: str) -> GitHubRepository:
        """Get repository information."""
        repo = self.repositories.get(repository_name)
        if not repo:
            raise ValueError(f"Repository {repository_name} not found")
        
        return self._convert_repository(repo)
