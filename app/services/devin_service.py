"""
Devin API integration service for creating and managing Devin sessions.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import structlog
import httpx
from httpx import AsyncClient

from ..config import settings
from ..models.devin_models import (
    DevinSession, DevinSessionStatus, DevinSessionRequest, DevinSessionResponse,
    DevinSessionDetails, DevinScopeResult, DevinCompletionResult, DevinMessage,
    DevinSessionType, DevinSessionSummary
)
from ..models.github_models import GitHubIssue
from .database_service import DatabaseService

logger = structlog.get_logger(__name__)


class DevinService:
    """Service for interacting with Devin API."""
    
    def __init__(self):
        """Initialize Devin service with API configuration."""
        self.base_url = settings.devin_api_base_url
        self.headers = settings.devin_headers
        self.active_sessions: Dict[str, DevinSession] = {}

        # Database service for persistent storage
        self.db_service = DatabaseService()

        # Log configuration (without exposing the full API key)
        api_key_preview = settings.devin_api_key[:10] + "..." if len(settings.devin_api_key) > 10 else "***"
        logger.info("Devin service initialized",
                   base_url=self.base_url,
                   api_key_preview=api_key_preview,
                   headers_configured=bool(self.headers))
        self.session_cache_ttl = timedelta(hours=1)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Devin API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"



        try:
            logger.info("Making Devin API request",
                       method=method,
                       url=url,
                       headers_present=bool(self.headers),
                       data_keys=list(data.keys()) if data else None)

            async with AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params
                )

                logger.info("Devin API response",
                           status_code=response.status_code,
                           response_size=len(response.content) if response.content else 0)

                if response.status_code == 200:
                    response_json = response.json()
                    logger.info("Devin API success", response_keys=list(response_json.keys()))
                    return response_json
                elif response.status_code == 400:
                    error_text = response.text
                    logger.error("Devin API bad request", error_response=error_text)
                    try:
                        error_data = response.json()
                        raise ValueError(f"Bad request: {error_data.get('error', 'Unknown error')}")
                    except:
                        raise ValueError(f"Bad request: {error_text}")
                elif response.status_code == 401:
                    logger.error("Devin API unauthorized", response_text=response.text)
                    raise ValueError("Unauthorized: Invalid Devin API key")
                elif response.status_code == 500:
                    logger.error("Devin API server error", response_text=response.text)
                    raise RuntimeError("Devin API server error")
                else:
                    logger.error("Devin API error",
                               status_code=response.status_code,
                               response_text=response.text)
                    raise RuntimeError(f"Devin API error: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Devin API request timeout", endpoint=endpoint)
            raise RuntimeError("Devin API request timeout")
        except Exception as e:
            logger.error("Devin API request failed", endpoint=endpoint, error=str(e), error_type=type(e).__name__)
            raise
    
    async def create_session(self, request: DevinSessionRequest) -> DevinSessionResponse:
        """
        Create a new Devin session.
        
        Args:
            request: Session creation request
            
        Returns:
            DevinSessionResponse with session details
        """
        try:
            # Prepare request data
            data = {
                "prompt": request.prompt,
                "idempotent": False
            }

            # Add tags if provided
            if request.tags:
                data["tags"] = request.tags
            
            logger.info("Creating Devin session",
                       session_type=request.session_type,
                       repository=request.repository_name,
                       issue_number=request.issue_number)

            # Print the HTTP request being made to Devin API
            print("\n" + "="*80)
            print("HTTP REQUEST TO DEVIN API:")
            print("="*80)
            print(f"Method: POST")
            print(f"URL: {self.base_url}/sessions")
            print(f"Headers: {self.headers}")
            print("Request Body:")
            import json
            print(json.dumps(data, indent=2))
            print("="*80)

            # Make API request
            response_data = await self._make_request("POST", "/sessions", data)
            
            # Create response object
            response = DevinSessionResponse(
                session_id=response_data["session_id"],
                url=response_data["url"],
                is_new_session=response_data.get("is_new_session", True)
            )
            
            # Create and cache session object
            session = DevinSession(
                session_id=response.session_id,
                status=DevinSessionStatus.PENDING,
                session_type=request.session_type,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                prompt=request.prompt,
                repository_name=request.repository_name,
                issue_number=request.issue_number,
                tags=request.tags,
                session_url=response.url,
                confidence_score=request.confidence_score
            )
            
            self.active_sessions[response.session_id] = session

            # Store session in database
            try:
                self.db_service.store_session(session)
                logger.info("Session stored in database", session_id=response.session_id)
            except Exception as db_error:
                logger.warning("Failed to store session in database",
                             session_id=response.session_id,
                             error=str(db_error))

            logger.info("Devin session created",
                       session_id=response.session_id,
                       is_new=response.is_new_session)

            return response
            
        except Exception as e:
            logger.error("Failed to create Devin session", error=str(e))
            raise
    
    async def get_session_details(self, session_id: str) -> DevinSessionDetails:
        """
        Get detailed information about a Devin session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            DevinSessionDetails object
        """
        try:
            # Make API request
            response_data = await self._make_request("GET", f"/sessions/{session_id}")
            
            # Parse response
            details = DevinSessionDetails(
                session_id=session_id,
                status=DevinSessionStatus(response_data.get("status", "pending")),
                created_at=datetime.fromisoformat(response_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(response_data["updated_at"].replace("Z", "+00:00")),
                url=response_data["url"],
                prompt=response_data.get("prompt", ""),
                output=response_data.get("output"),
                error_message=response_data.get("error_message")
            )
            
            # Add completion time if available
            if response_data.get("completed_at"):
                details.completed_at = datetime.fromisoformat(
                    response_data["completed_at"].replace("Z", "+00:00")
                )
            
            # Update cached session if exists
            if session_id in self.active_sessions:
                cached_session = self.active_sessions[session_id]
                cached_session.status = details.status
                cached_session.updated_at = details.updated_at
                cached_session.completed_at = details.completed_at
                cached_session.output = details.output
                cached_session.error_message = details.error_message
            
            logger.info("Retrieved session details", 
                       session_id=session_id,
                       status=details.status)
            
            return details
            
        except Exception as e:
            logger.error("Failed to get session details",
                        session_id=session_id,
                        error=str(e))
            raise

    async def send_message(self, session_id: str, message: str) -> bool:
        """
        Send a message to an active Devin session.

        Args:
            session_id: ID of the session
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        try:
            data = {"message": message}
            await self._make_request("POST", f"/sessions/{session_id}/messages", data)

            logger.info("Message sent to session",
                       session_id=session_id,
                       message_length=len(message))
            return True

        except Exception as e:
            logger.error("Failed to send message to session",
                        session_id=session_id,
                        error=str(e))
            raise

    async def list_sessions(self) -> List[DevinSessionSummary]:
        """
        List all sessions for the organization.

        Returns:
            List of session summaries
        """
        try:
            response_data = await self._make_request("GET", "/sessions")

            sessions = []
            for session_data in response_data.get("sessions", []):
                summary = DevinSessionSummary(
                    session_id=session_data["session_id"],
                    session_type=DevinSessionType.GENERAL,  # Default, may need to be stored
                    status=DevinSessionStatus(session_data.get("status", "pending")),
                    created_at=datetime.fromisoformat(
                        session_data["created_at"].replace("Z", "+00:00")
                    )
                )
                sessions.append(summary)

            return sessions

        except Exception as e:
            logger.error("Failed to list sessions", error=str(e))
            raise

    async def scope_github_issue(self, issue: GitHubIssue) -> DevinScopeResult:
        """
        Create a Devin session to scope a GitHub issue and assign confidence score.

        Args:
            issue: GitHub issue to scope

        Returns:
            DevinScopeResult with scoping analysis
        """
        try:
            # Create detailed prompt for issue scoping
            prompt = self._create_scoping_prompt(issue)

            # Create session request
            request = DevinSessionRequest(
                prompt=prompt,
                session_type=DevinSessionType.SCOPE_ISSUE,
                repository_name=issue.repository.full_name if issue.repository else None,
                issue_number=issue.number,
                issue_title=issue.title,
                issue_body=issue.body,
                issue_labels=[label.name for label in issue.labels],
                tags=["scoping", "analysis", f"issue-{issue.number}"]
            )

            # Create session
            response = await self.create_session(request)

            # Wait for initial analysis (with timeout)
            start_time = datetime.now()
            timeout = timedelta(seconds=settings.analysis_timeout)

            while datetime.now() - start_time < timeout:
                details = await self.get_session_details(response.session_id)

                if details.status == DevinSessionStatus.COMPLETED:
                    # Parse scoping results from output
                    return self._parse_scoping_results(details, issue)
                elif details.status == DevinSessionStatus.FAILED:
                    raise RuntimeError(f"Scoping session failed: {details.error_message}")

                # Wait before checking again
                await asyncio.sleep(10)

            # Timeout reached
            logger.warning("Scoping session timeout",
                          session_id=response.session_id,
                          issue_number=issue.number)

            # Return partial results
            return DevinScopeResult(
                session_id=response.session_id,
                issue_number=issue.number,
                repository_name=issue.repository.full_name if issue.repository else "unknown",
                confidence_score=0.5,  # Default medium confidence
                complexity_estimate="medium",
                requirements_clarity=0.5,
                technical_feasibility=0.5,
                scope_completeness=0.5,
                action_plan=["Analysis in progress..."],
                acceptance_criteria=["To be determined..."],
                created_at=datetime.now(),
                analysis_duration_minutes=(datetime.now() - start_time).total_seconds() / 60
            )

        except Exception as e:
            logger.error("Failed to scope GitHub issue",
                        issue_number=issue.number,
                        error=str(e))
            raise

    async def complete_github_issue(
        self,
        issue: GitHubIssue,
        scope_result: DevinScopeResult
    ) -> DevinCompletionResult:
        """
        Create a Devin session to complete a GitHub issue based on scoping results.

        Args:
            issue: GitHub issue to complete
            scope_result: Previous scoping analysis

        Returns:
            DevinCompletionResult with completion status
        """
        try:
            # Create detailed prompt for issue completion
            prompt = self._create_completion_prompt(issue, scope_result)

            # Create session request
            request = DevinSessionRequest(
                prompt=prompt,
                session_type=DevinSessionType.COMPLETE_ISSUE,
                repository_name=issue.repository.full_name if issue.repository else None,
                issue_number=issue.number,
                issue_title=issue.title,
                issue_body=issue.body,
                issue_labels=[label.name for label in issue.labels],
                confidence_score=scope_result.confidence_score,
                tags=["completion", "implementation", f"issue-{issue.number}"]
            )

            # Create session
            response = await self.create_session(request)

            logger.info("Started issue completion session",
                       session_id=response.session_id,
                       issue_number=issue.number,
                       confidence_score=scope_result.confidence_score)

            # Return initial completion result (session will continue in background)
            return DevinCompletionResult(
                session_id=response.session_id,
                issue_number=issue.number,
                repository_name=issue.repository.full_name if issue.repository else "unknown",
                status=DevinSessionStatus.RUNNING,
                completion_percentage=0.0,
                created_at=datetime.now(),
                completion_duration_minutes=0.0
            )

        except Exception as e:
            logger.error("Failed to start issue completion",
                        issue_number=issue.number,
                        error=str(e))
            raise

    def _create_scoping_prompt(self, issue: GitHubIssue) -> str:
        """Create an enhanced detailed prompt for issue scoping with context."""
        repository_name = issue.repository.full_name if issue.repository else 'Unknown'

        # Get relevant files from database
        relevant_files = self.db_service.get_relevant_files(repository_name, limit=15)

        # Get previous scoping summaries
        previous_summaries = self.db_service.get_previous_scoping_summaries(repository_name, limit=3)

        # Build file paths section
        files_section = ""
        if relevant_files:
            files_section = "\n**RELEVANT REPOSITORY FILES:**\n"
            for file_info in relevant_files:
                files_section += f"- {file_info['path']}"
                if file_info.get('description'):
                    files_section += f" - {file_info['description']}"
                if file_info.get('language'):
                    files_section += f" ({file_info['language']})"
                files_section += "\n"

        # Build previous summaries section
        summaries_section = ""
        if previous_summaries:
            summaries_section = "\n**PREVIOUS SCOPING INSIGHTS:**\n"
            for i, summary in enumerate(previous_summaries, 1):
                summaries_section += f"{i}. Issue #{summary['issue_number']} ({summary['complexity_estimate']} complexity, {summary['confidence_score']:.1f}% confidence):\n"
                if summary.get('recommended_approach'):
                    summaries_section += f"   Approach: {summary['recommended_approach'][:100]}...\n"
                if summary.get('key_challenges'):
                    summaries_section += f"   Challenges: {', '.join(summary['key_challenges'])}\n"
                summaries_section += "\n"

        prompt = f"""You are acting as a senior software engineer assigned to scoping Github issue {issue.title} in the `{repository_name}` repository.

Your task is to:
- Read and understand the issue description and any linked context.
- Break the work down into clear, actionable technical steps.
- Identify any missing information or blockers.
- Estimate effort and complexity for Devin AI to implement it.
- Assign a confidence score from 0–100% based on:
    - Completeness of the requirements
    - Familiarity of the code area
    - Level of ambiguity
    - Known risks

**Issue Details:**
- Repository: {repository_name}
- Issue #{issue.number}: {issue.title}
- Created by: {issue.user.login}
- Labels: {", ".join([label.name for label in issue.labels]) if issue.labels else "None"}
- Assignees: {", ".join([assignee.login for assignee in issue.assignees]) if issue.assignees else "None"}
- Comments: {issue.comments}

**Issue Description:**
{issue.body or 'No description provided'}
{files_section}{summaries_section}
**IMPLEMENTATION GUIDANCE:**
Your scoping should provide specific next steps that another Devin AI session can follow to implement this issue, including:
1. Exact files to modify or create
2. Specific functions/classes to implement
3. Dependencies or libraries needed
4. Testing approach and test files to create
5. Step-by-step implementation sequence

To submit your work, provide a detailed report outlining the breakdown of work, identified missing information/blockers, effort/complexity estimates, and the confidence score."""
        return prompt.strip()

    def _create_specific_scoping_prompt(self, repository_name: str, issue_number: int, issue_title: str) -> str:
        """Create an enhanced scoping prompt with file paths and previous summaries."""

        # Get relevant files from database
        relevant_files = self.db_service.get_relevant_files(repository_name, limit=15)

        # Get previous scoping summaries
        previous_summaries = self.db_service.get_previous_scoping_summaries(repository_name, limit=3)

        # Build file paths section
        files_section = ""
        if relevant_files:
            files_section = "\n**RELEVANT REPOSITORY FILES:**\n"
            for file_info in relevant_files:
                files_section += f"- {file_info['path']}"
                if file_info.get('description'):
                    files_section += f" - {file_info['description']}"
                if file_info.get('language'):
                    files_section += f" ({file_info['language']})"
                files_section += "\n"

        # Build previous summaries section
        summaries_section = ""
        if previous_summaries:
            summaries_section = "\n**PREVIOUS SCOPING INSIGHTS:**\n"
            for i, summary in enumerate(previous_summaries, 1):
                summaries_section += f"{i}. Issue #{summary['issue_number']} ({summary['complexity_estimate']} complexity, {summary['confidence_score']:.1f}% confidence):\n"
                if summary.get('recommended_approach'):
                    summaries_section += f"   Approach: {summary['recommended_approach'][:100]}...\n"
                if summary.get('key_challenges'):
                    summaries_section += f"   Challenges: {', '.join(summary['key_challenges'])}\n"
                summaries_section += "\n"

        prompt = f"""You are acting as a senior software engineer assigned to scoping Github issue {issue_title} in the `{repository_name}` repository.

Your task is to:
- Read and understand the issue description and any linked context.
- Break the work down into clear, actionable technical steps.
- Identify any missing information or blockers.
- Estimate effort and complexity for Devin AI to implement it.
- Assign a confidence score from 0–100% based on:
    - Completeness of the requirements
    - Familiarity of the code area
    - Level of ambiguity
    - Known risks
{files_section}{summaries_section}
**IMPLEMENTATION GUIDANCE:**
Your scoping should provide specific next steps that another Devin AI session can follow to implement this issue, including:
1. Exact files to modify or create
2. Specific functions/classes to implement
3. Dependencies or libraries needed
4. Testing approach and test files to create
5. Step-by-step implementation sequence

To submit your work, provide a detailed report outlining the breakdown of work, identified missing information/blockers, effort/complexity estimates, and the confidence score."""

        # Print the complete generated prompt to terminal
        print("\n" + "="*80)
        print("📝 GENERATED PROMPT FOR DEVIN API:")
        print("="*80)
        print(f"Repository: {repository_name}")
        print(f"Issue: #{issue_number} - {issue_title}")
        print("-" * 80)
        print(prompt)
        print("="*80)

        # Debug log to verify prompt generation
        logger.info("Generated scoping prompt",
                   repository_name=repository_name,
                   issue_number=issue_number,
                   issue_title=issue_title,
                   prompt_preview=prompt[:200] + "..." if len(prompt) > 200 else prompt)

        return prompt.strip()

    async def create_specific_scoping_session(self, repository_name: str, issue_number: int, issue_title: str) -> DevinSessionResponse:
        """Create a Devin session for scoping a specific issue."""
        try:
            prompt = self._create_specific_scoping_prompt(repository_name, issue_number, issue_title)

            request = DevinSessionRequest(
                prompt=prompt,
                session_type=DevinSessionType.SCOPE_ISSUE,
                repository_name=repository_name,
                issue_number=issue_number,
                issue_title=issue_title,
                tags=["scoping", "analysis", f"issue-{issue_number}", "sales-analytics"]
            )

            logger.info("Creating specific scoping session",
                       repository=repository_name,
                       issue_number=issue_number,
                       issue_title=issue_title)

            return await self.create_session(request)

        except Exception as e:
            logger.error("Failed to create specific scoping session",
                        repository=repository_name,
                        issue_number=issue_number,
                        error=str(e))
            raise

    def _create_completion_prompt(self, issue: GitHubIssue, scope_result: DevinScopeResult) -> str:
        """Create a detailed prompt for issue completion with specific implementation steps."""
        repository_name = issue.repository.full_name if issue.repository else 'Unknown'

        # Get relevant files for implementation context
        relevant_files = self.db_service.get_relevant_files(repository_name, limit=10)

        # Build files context section
        files_context = ""
        if relevant_files:
            files_context = "\n**RELEVANT FILES FOR IMPLEMENTATION:**\n"
            for file_info in relevant_files:
                files_context += f"- {file_info['path']}"
                if file_info.get('description'):
                    files_context += f" - {file_info['description']}"
                files_context += "\n"

        prompt = f"""
You are implementing GitHub issue #{issue.number}: {issue.title} in the `{repository_name}` repository.

**IMPLEMENTATION CONTEXT:**
- Repository: {repository_name}
- Confidence Score: {scope_result.confidence_score}
- Complexity: {scope_result.complexity_estimate}
- Estimated Hours: {scope_result.estimated_hours or 'Not specified'}

**ISSUE DESCRIPTION:**
{issue.body or 'No description provided'}

**SCOPING ANALYSIS:**
- Recommended Approach: {scope_result.recommended_approach or 'See action plan'}
- Potential Challenges: {', '.join(scope_result.potential_challenges) if scope_result.potential_challenges else 'None identified'}
- Required Knowledge: {', '.join(scope_result.required_knowledge) if scope_result.required_knowledge else 'Standard development skills'}
- Dependencies: {', '.join(scope_result.dependencies) if scope_result.dependencies else 'None identified'}
{files_context}
**DETAILED ACTION PLAN:**
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(scope_result.action_plan))}

**ACCEPTANCE CRITERIA:**
{chr(10).join(f"- {criteria}" for criteria in scope_result.acceptance_criteria)}

**IMPLEMENTATION REQUIREMENTS:**
1. **Code Changes**: Follow the action plan step by step, making precise changes to the identified files
2. **Testing**: Create comprehensive tests for all new functionality, including unit tests and integration tests
3. **Documentation**: Update relevant documentation, including README files, API docs, and inline comments
4. **Error Handling**: Implement proper error handling and validation for all new code paths
5. **Code Quality**: Follow the repository's coding standards and best practices
6. **Performance**: Consider performance implications and optimize where necessary
7. **Security**: Ensure all changes follow security best practices
8. **Backwards Compatibility**: Maintain backwards compatibility unless explicitly stated otherwise

**DELIVERABLES:**
- All code changes implemented according to the action plan
- Comprehensive test suite with good coverage
- Updated documentation
- Clean, well-commented code
- Pull request with detailed description of changes

**NEXT STEPS FOR ANOTHER DEVIN SESSION:**
If this implementation needs to be continued by another Devin AI session, ensure you:
1. Document exactly what was completed and what remains
2. Provide clear instructions for the next steps
3. List any blockers or issues encountered
4. Update the issue with progress status

Please proceed with implementing this issue systematically, following the action plan and meeting all acceptance criteria.
"""
        return prompt.strip()

    def _parse_scoping_results(self, details: DevinSessionDetails, issue: GitHubIssue) -> DevinScopeResult:
        """Parse scoping results from Devin session output."""
        # This is a simplified parser - in a real implementation, you might use
        # structured output from Devin or more sophisticated parsing

        output = details.output or ""

        # Extract confidence score (default to 0.7 if not found)
        confidence_score = 0.7
        if "confidence" in output.lower():
            # Simple regex or string parsing could be used here
            # For now, using a default value
            pass

        # Extract complexity estimate
        complexity_estimate = "medium"
        if "low complexity" in output.lower() or "simple" in output.lower():
            complexity_estimate = "low"
        elif "high complexity" in output.lower() or "complex" in output.lower():
            complexity_estimate = "high"

        # Create result with parsed or default values
        return DevinScopeResult(
            session_id=details.session_id,
            issue_number=issue.number,
            repository_name=issue.repository.full_name if issue.repository else "unknown",
            confidence_score=confidence_score,
            complexity_estimate=complexity_estimate,
            estimated_hours=None,  # Could be parsed from output
            requirements_clarity=0.8,  # Default values - could be parsed
            technical_feasibility=0.8,
            scope_completeness=0.7,
            recommended_approach="Follow standard development practices",
            potential_challenges=["Integration complexity", "Testing requirements"],
            required_knowledge=["Python", "Web development"],
            dependencies=[],
            action_plan=[
                "Analyze requirements",
                "Design solution",
                "Implement changes",
                "Write tests",
                "Create pull request"
            ],
            acceptance_criteria=[
                "All requirements implemented",
                "Tests pass",
                "Code review approved"
            ],
            created_at=details.created_at,
            analysis_duration_minutes=(
                (details.completed_at or datetime.now()) - details.created_at
            ).total_seconds() / 60
        )

    def get_cached_session(self, session_id: str) -> Optional[DevinSession]:
        """Get a cached session if available and not expired."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if datetime.now() - session.updated_at < self.session_cache_ttl:
                return session
            else:
                # Remove expired session
                del self.active_sessions[session_id]
        return None

    async def get_session_status(self, session_id: str) -> DevinSessionStatus:
        """Get the current status of a session."""
        try:
            details = await self.get_session_details(session_id)
            return details.status
        except Exception as e:
            logger.error("Failed to get session status",
                        session_id=session_id,
                        error=str(e))
            return DevinSessionStatus.FAILED
