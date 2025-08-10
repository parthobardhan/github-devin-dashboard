"""
Devin API routes for the dashboard.
"""

from typing import List, Optional, Dict, Any
import structlog
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from ..models.devin_models import (
    DevinSession, DevinSessionRequest, DevinSessionResponse, DevinSessionDetails,
    DevinScopeResult, DevinCompletionResult, DevinSessionSummary, DevinSessionType
)
from ..services.devin_service import DevinService
from ..services.session_service import SessionService
from ..services.database_service import DatabaseService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Dependencies
def get_devin_service() -> DevinService:
    return DevinService()

def get_session_service() -> SessionService:
    return SessionService()

def get_database_service() -> DatabaseService:
    return DatabaseService()


class ScopeIssueRequest(BaseModel):
    """Request to scope a GitHub issue."""
    repository_name: str
    issue_number: int


class ScopeSpecificIssueRequest(BaseModel):
    """Request to scope a specific GitHub issue with custom details."""
    repository_name: str
    issue_number: int
    issue_title: str


class CompleteIssueRequest(BaseModel):
    """Request to complete a GitHub issue."""
    repository_name: str
    issue_number: int
    use_existing_scope: bool = True


class SendMessageRequest(BaseModel):
    """Request to send a message to a session."""
    message: str


class StartDevinImplementRequest(BaseModel):
    """Request to start Devin implementation for an issue."""
    repository_name: str
    issue_number: int


@router.get("/sessions", response_model=List[DevinSessionSummary])
async def list_sessions(
    devin_service: DevinService = Depends(get_devin_service)
):
    """List all Devin sessions."""
    try:
        sessions = await devin_service.list_sessions()
        
        logger.info("Listed Devin sessions", count=len(sessions))
        return sessions
        
    except Exception as e:
        logger.error("Failed to list sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.post("/sessions", response_model=DevinSessionResponse)
async def create_session(
    request: DevinSessionRequest,
    devin_service: DevinService = Depends(get_devin_service)
):
    """Create a new Devin session."""
    try:
        response = await devin_service.create_session(request)
        
        logger.info("Created Devin session", 
                   session_id=response.session_id,
                   session_type=request.session_type)
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/sessions/{session_id}", response_model=DevinSessionDetails)
async def get_session(
    session_id: str,
    devin_service: DevinService = Depends(get_devin_service)
):
    """Get details about a specific session."""
    try:
        details = await devin_service.get_session_details(session_id)

        logger.info("Retrieved session details",
                   session_id=session_id,
                   status=details.status)

        return details

    except Exception as e:
        logger.error("Failed to get session details",
                    session_id=session_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get session details")


@router.get("/sessions/{session_id}/database", response_model=DevinSession)
async def get_session_from_database(
    session_id: str,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get session data from the database."""
    try:
        session = db_service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found in database")

        logger.info("Retrieved session from database",
                   session_id=session_id,
                   status=session.status)

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session from database",
                    session_id=session_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get session from database")


@router.get("/repositories/{repository_name}/sessions", response_model=List[DevinSession])
async def get_repository_sessions(
    repository_name: str,
    limit: int = 10,
    db_service: DatabaseService = Depends(get_database_service)
):
    """Get recent sessions for a repository from the database."""
    try:
        # Replace URL encoding
        repository_name = repository_name.replace("%2F", "/")

        sessions = db_service.get_sessions_by_repository(repository_name, limit=limit)

        logger.info("Retrieved repository sessions from database",
                   repository=repository_name,
                   count=len(sessions))

        return sessions

    except Exception as e:
        logger.error("Failed to get repository sessions from database",
                    repository=repository_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get repository sessions")


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    devin_service: DevinService = Depends(get_devin_service)
):
    """Send a message to an active session."""
    try:
        success = await devin_service.send_message(session_id, request.message)
        
        if success:
            return {"status": "success", "message": "Message sent successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to send message")
            
    except Exception as e:
        logger.error("Failed to send message", 
                    session_id=session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.get("/test-api-connectivity")
async def test_devin_api_connectivity(
    devin_service: DevinService = Depends(get_devin_service)
) -> Dict[str, Any]:
    """Test connectivity to the Devin API by listing sessions."""
    try:
        # Test the list sessions endpoint
        sessions = await devin_service.list_sessions()

        return {
            "success": True,
            "message": "Devin API connectivity test successful",
            "sessions_count": len(sessions),
            "api_status": "connected"
        }

    except Exception as e:
        logger.error("Devin API connectivity test failed", error=str(e))
        return {
            "success": False,
            "message": f"Devin API connectivity test failed: {str(e)}",
            "sessions_count": 0,
            "api_status": "disconnected"
        }


@router.post("/scope-issue", response_model=DevinScopeResult)
async def scope_issue(
    request: ScopeIssueRequest,
    background_tasks: BackgroundTasks,
    session_service: SessionService = Depends(get_session_service)
):
    """Trigger a Devin session to scope a GitHub issue."""
    try:
        # Validate repository name format
        if "/" not in request.repository_name:
            raise HTTPException(
                status_code=400, 
                detail="Repository name must be in format 'owner/repo'"
            )
        
        # Validate issue number
        if request.issue_number <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Issue number must be positive"
            )
        
        logger.info("Starting issue scoping", 
                   repository=request.repository_name,
                   issue_number=request.issue_number)
        
        # Trigger scoping session
        scope_result = await session_service.trigger_issue_scoping(
            request.repository_name, 
            request.issue_number
        )
        
        return scope_result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to scope issue", 
                    repository=request.repository_name,
                    issue_number=request.issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to scope issue")


@router.post("/scope-specific-issue")
async def scope_specific_issue(
    request: ScopeSpecificIssueRequest,
    background_tasks: BackgroundTasks,
    session_service: SessionService = Depends(get_session_service)
):
    """Trigger a Devin session to scope a specific GitHub issue with custom prompt."""
    try:
        # Validate repository name format
        if "/" not in request.repository_name:
            raise HTTPException(
                status_code=400,
                detail="Repository name must be in format 'owner/repo'"
            )

        # Validate issue number
        if request.issue_number <= 0:
            raise HTTPException(
                status_code=400,
                detail="Issue number must be positive"
            )

        # Print the complete request body to terminal
        print("\n" + "="*80)
        print("🔍 POST /api/devin/scope-specific-issue REQUEST BODY:")
        print("="*80)
        print(f"Repository Name: {request.repository_name}")
        print(f"Issue Number: {request.issue_number}")
        print(f"Issue Title: {request.issue_title}")
        print("="*80)

        logger.info("Starting specific issue scoping",
                   repository=request.repository_name,
                   issue_number=request.issue_number,
                   issue_title=request.issue_title)

        # Debug log to verify the prompt generation
        logger.info("Request details for prompt generation",
                   repository_name=request.repository_name,
                   issue_number=request.issue_number,
                   issue_title=request.issue_title)

        # Create Devin session using the specific scoping method
        devin_service = session_service.devin_service
        session_response = await devin_service.create_specific_scoping_session(
            request.repository_name,
            request.issue_number,
            request.issue_title
        )

        logger.info("Specific scoping session created",
                   session_id=session_response.session_id,
                   repository=request.repository_name,
                   issue_number=request.issue_number)

        return {
            "session_id": session_response.session_id,
            "session_url": session_response.url,
            "repository_name": request.repository_name,
            "issue_number": request.issue_number,
            "issue_title": request.issue_title,
            "status": "scoping_started",
            "message": f"Scoping session started for issue #{request.issue_number}: {request.issue_title}"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to scope specific issue",
                    repository=request.repository_name,
                    issue_number=request.issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to scope specific issue")


@router.delete("/clear-scope-data")
async def clear_scope_data(
    session_service: SessionService = Depends(get_session_service)
):
    """Clear all existing scoping data from the dashboard."""
    try:
        logger.info("Clearing all scoping data")

        # Use the service method to clear data and get counts
        cleared_counts = session_service.clear_all_scoping_data()

        total_cleared = sum(cleared_counts.values())

        return {
            "status": "success",
            "message": f"Successfully cleared {total_cleared} items of scoping data",
            "cleared_counts": cleared_counts,
            "details": {
                "issue_analyses": f"{cleared_counts['issue_analyses']} analyses cleared",
                "session_results": f"{cleared_counts['session_results']} results cleared",
                "active_sessions": f"{cleared_counts['active_sessions']} sessions cleared"
            }
        }

    except Exception as e:
        logger.error("Failed to clear scope data", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear scope data")


@router.post("/generate-analysis")
async def generate_analysis(
    request: ScopeIssueRequest,
    session_service: SessionService = Depends(get_session_service)
):
    """Generate analysis for a specific issue without creating a Devin session."""
    try:
        # Validate repository name format
        if "/" not in request.repository_name:
            raise HTTPException(
                status_code=400,
                detail="Repository name must be in format 'owner/repo'"
            )

        # Validate issue number
        if request.issue_number <= 0:
            raise HTTPException(
                status_code=400,
                detail="Issue number must be positive"
            )

        logger.info("Generating analysis for issue",
                   repository=request.repository_name,
                   issue_number=request.issue_number)

        # Generate analysis
        success = await session_service.generate_issue_analysis(
            request.repository_name,
            request.issue_number
        )

        if success:
            return {
                "status": "success",
                "repository_name": request.repository_name,
                "issue_number": request.issue_number,
                "message": f"Analysis generated for issue #{request.issue_number}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate analysis"
            )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to generate analysis",
                    repository=request.repository_name,
                    issue_number=request.issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate analysis")


@router.post("/complete-issue", response_model=DevinCompletionResult)
async def complete_issue(
    request: CompleteIssueRequest,
    background_tasks: BackgroundTasks,
    session_service: SessionService = Depends(get_session_service)
):
    """Trigger a Devin session to complete a GitHub issue."""
    try:
        # Validate repository name format
        if "/" not in request.repository_name:
            raise HTTPException(
                status_code=400, 
                detail="Repository name must be in format 'owner/repo'"
            )
        
        # Validate issue number
        if request.issue_number <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Issue number must be positive"
            )
        
        logger.info("Starting issue completion", 
                   repository=request.repository_name,
                   issue_number=request.issue_number,
                   use_existing_scope=request.use_existing_scope)
        
        # Trigger completion session
        completion_result = await session_service.trigger_issue_completion(
            request.repository_name, 
            request.issue_number,
            request.use_existing_scope
        )
        
        return completion_result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to complete issue", 
                    repository=request.repository_name,
                    issue_number=request.issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete issue")


@router.get("/sessions/{session_id}/status")
async def get_session_status(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
):
    """Get the current status of a session."""
    try:
        session = await session_service.get_session_status(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session.session_id,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "completed_at": session.completed_at,
            "session_url": session.session_url,
            "progress_percentage": getattr(session, 'progress_percentage', None),
            "error_message": session.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get session status", 
                    session_id=session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get session status")


@router.post("/batch-scope")
async def batch_scope_issues(
    repository_name: str,
    issue_numbers: List[int],
    background_tasks: BackgroundTasks,
    session_service: SessionService = Depends(get_session_service)
):
    """Trigger scoping for multiple issues in batch."""
    try:
        # Validate repository name format
        if "/" not in repository_name:
            raise HTTPException(
                status_code=400, 
                detail="Repository name must be in format 'owner/repo'"
            )
        
        # Validate issue numbers
        if not issue_numbers or len(issue_numbers) > 10:
            raise HTTPException(
                status_code=400, 
                detail="Must provide 1-10 issue numbers"
            )
        
        for issue_number in issue_numbers:
            if issue_number <= 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Issue number {issue_number} must be positive"
                )
        
        logger.info("Starting batch issue scoping", 
                   repository=repository_name,
                   issue_count=len(issue_numbers))
        
        # Start scoping sessions in background
        session_ids = []
        for issue_number in issue_numbers:
            try:
                background_tasks.add_task(
                    session_service.trigger_issue_scoping,
                    repository_name,
                    issue_number
                )
                session_ids.append(f"batch-{repository_name}-{issue_number}")
            except Exception as e:
                logger.warning("Failed to queue scoping for issue", 
                              issue_number=issue_number, 
                              error=str(e))
        
        return {
            "status": "queued",
            "repository_name": repository_name,
            "issue_numbers": issue_numbers,
            "queued_sessions": len(session_ids),
            "message": f"Queued {len(session_ids)} scoping sessions"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to batch scope issues", 
                    repository=repository_name,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to batch scope issues")


@router.get("/stats")
async def get_devin_stats(
    devin_service: DevinService = Depends(get_devin_service)
):
    """Get Devin session statistics."""
    try:
        sessions = await devin_service.list_sessions()
        
        # Calculate statistics
        total_sessions = len(sessions)
        status_counts = {}
        
        for session in sessions:
            status = session.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "status_breakdown": status_counts,
            "active_sessions": status_counts.get("running", 0),
            "completed_sessions": status_counts.get("completed", 0),
            "failed_sessions": status_counts.get("failed", 0),
            "success_rate": (
                status_counts.get("completed", 0) / 
                max(1, status_counts.get("completed", 0) + status_counts.get("failed", 0))
            ),
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error("Failed to get Devin stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get Devin statistics")


@router.post("/start-implement")
async def start_devin_implement(
    request: StartDevinImplementRequest,
    background_tasks: BackgroundTasks,
    devin_service: DevinService = Depends(get_devin_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    """Start Devin implementation for an issue based on previous session confidence."""
    try:
        # Validate repository name format
        if "/" not in request.repository_name:
            raise HTTPException(
                status_code=400,
                detail="Repository name must be in format 'owner/repo'"
            )

        # Validate issue number
        if request.issue_number <= 0:
            raise HTTPException(
                status_code=400,
                detail="Issue number must be positive"
            )

        logger.info("Starting Devin implementation",
                   repository=request.repository_name,
                   issue_number=request.issue_number)

        # Get the most recent session for this issue from database
        most_recent_session = db_service.get_most_recent_session_for_issue(
            request.repository_name,
            request.issue_number
        )

        if not most_recent_session:
            raise HTTPException(
                status_code=404,
                detail=f"No previous session found for issue #{request.issue_number}"
            )

        logger.info("Found most recent session",
                   session_id=most_recent_session.session_id,
                   repository=request.repository_name,
                   issue_number=request.issue_number)

        # Get fresh session details from Devin API to get current confidence_score
        try:
            session_details = await devin_service.get_session_details(most_recent_session.session_id)
            confidence_score = session_details.confidence_score

            logger.info("Retrieved session details from Devin API",
                       session_id=most_recent_session.session_id,
                       confidence_score=confidence_score)

        except Exception as api_error:
            logger.warning("Failed to get session details from Devin API, using cached confidence",
                          session_id=most_recent_session.session_id,
                          error=str(api_error))
            confidence_score = most_recent_session.confidence_score

        # Return confidence score as structured data
        response_data = {
            "session_id": most_recent_session.session_id,
            "confidence_score": confidence_score,
            "repository_name": request.repository_name,
            "issue_number": request.issue_number
        }

        # Check if confidence score is > 70
        if confidence_score and confidence_score > 70:
            logger.info("Confidence score > 70, creating implementation session",
                       confidence_score=confidence_score)

            # Get previous work summaries and file paths from the database
            previous_summaries = db_service.get_previous_scoping_summaries(
                request.repository_name, limit=3
            )

            relevant_files = db_service.get_relevant_files(
                request.repository_name, limit=10
            )

            # Build enhanced prompt for implementation
            file_paths = [f["file_path"] for f in relevant_files if "file_path" in f]

            implementation_prompt = f"""
# Implementation Task for Issue #{request.issue_number}

## Repository: {request.repository_name}

## Previous Session Analysis
- Session ID: {most_recent_session.session_id}
- Confidence Score: {confidence_score}%
- Previous Analysis: {most_recent_session.output or 'No previous output available'}

## Relevant File Paths
{chr(10).join(f"- {path}" for path in file_paths[:10]) if file_paths else "- No specific file paths identified"}

## Previous Work Summaries
{chr(10).join(f"- Issue #{summary.get('issue_number', 'N/A')}: {summary.get('recommended_approach', 'No approach specified')}" for summary in previous_summaries[:3]) if previous_summaries else "- No previous work summaries available"}

## Implementation Instructions
1. Create a separate branch in github repository parthobardhan/inventory-app
2. Implement the solution based on the previous scoping analysis
3. Ensure all code follows best practices and includes appropriate tests
4. Create a pull request with detailed description of changes
5. Verify the solution addresses all requirements from the original issue

## Specific Next Steps
Based on the previous session analysis, focus on:
- Implementing the core functionality identified in the scoping phase
- Adding comprehensive error handling
- Writing unit tests for new functionality
- Updating documentation as needed

Please proceed with the implementation and create the branch as specified.
"""

            # Create implementation session
            try:
                session_request = DevinSessionRequest(
                    prompt=implementation_prompt,
                    session_type=DevinSessionType.COMPLETION,
                    repository_name=request.repository_name,
                    issue_number=request.issue_number,
                    tags=["implementation", "auto-generated"],
                    confidence_score=confidence_score
                )

                implementation_session = await devin_service.create_session(session_request)

                response_data.update({
                    "implementation_started": True,
                    "implementation_session_id": implementation_session.session_id,
                    "implementation_session_url": implementation_session.session_url,
                    "message": f"Implementation session created with confidence score {confidence_score}%"
                })

                logger.info("Implementation session created successfully",
                           implementation_session_id=implementation_session.session_id,
                           original_session_id=most_recent_session.session_id)

            except Exception as impl_error:
                logger.error("Failed to create implementation session",
                           error=str(impl_error))
                response_data.update({
                    "implementation_started": False,
                    "error": f"Failed to create implementation session: {str(impl_error)}"
                })
        else:
            logger.info("Confidence score <= 70, not creating implementation session",
                       confidence_score=confidence_score)
            response_data.update({
                "implementation_started": False,
                "message": f"Confidence score ({confidence_score}%) is not high enough (>70%) for automatic implementation"
            })

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start Devin implementation",
                    repository=request.repository_name,
                    issue_number=request.issue_number,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start Devin implementation: {str(e)}")
