"""
Database service for managing session data, scoping results, and file analysis.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import structlog

from ..database import (
    db_manager, DevinSessionDB, ScopingResultDB, 
    RepositoryFileDB, PreviousScopingDB
)
from ..models.devin_models import (
    DevinSession, DevinSessionStatus, DevinSessionType,
    DevinScopeResult
)

logger = structlog.get_logger(__name__)


class DatabaseService:
    """Service for database operations related to sessions and scoping."""
    
    def __init__(self):
        """Initialize database service."""
        # Ensure database is initialized
        db_manager.initialize()
    
    def store_session(self, session: DevinSession) -> bool:
        """Store a Devin session in the database."""
        try:
            db_session = db_manager.get_session()
            
            # Create database record
            db_record = DevinSessionDB(
                session_id=session.session_id,
                status=session.status.value,
                session_type=session.session_type.value,
                created_at=session.created_at,
                updated_at=session.updated_at,
                completed_at=session.completed_at,
                prompt=session.prompt,
                repository_name=session.repository_name,
                issue_number=session.issue_number,
                tags=session.tags,
                output=session.output,
                error_message=session.error_message,
                confidence_score=session.confidence_score,
                session_url=session.session_url,
                github_issue_url=session.github_issue_url,
                duration_minutes=session.duration_minutes,
                estimated_completion_time=session.estimated_completion_time
            )
            
            # Use merge to handle updates if session already exists
            db_session.merge(db_record)
            db_session.commit()
            
            logger.info("Session stored in database", 
                       session_id=session.session_id,
                       repository=session.repository_name,
                       issue_number=session.issue_number)
            
            return True
            
        except Exception as e:
            logger.error("Failed to store session in database", 
                        session_id=session.session_id,
                        error=str(e))
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def get_session(self, session_id: str) -> Optional[DevinSession]:
        """Retrieve a session from the database."""
        try:
            db_session = db_manager.get_session()
            
            db_record = db_session.query(DevinSessionDB).filter(
                DevinSessionDB.session_id == session_id
            ).first()
            
            if not db_record:
                return None
            
            # Convert to Pydantic model
            return DevinSession(
                session_id=db_record.session_id,
                status=DevinSessionStatus(db_record.status),
                session_type=DevinSessionType(db_record.session_type),
                created_at=db_record.created_at,
                updated_at=db_record.updated_at,
                completed_at=db_record.completed_at,
                prompt=db_record.prompt,
                repository_name=db_record.repository_name,
                issue_number=db_record.issue_number,
                tags=db_record.tags or [],
                output=db_record.output,
                error_message=db_record.error_message,
                confidence_score=db_record.confidence_score,
                session_url=db_record.session_url,
                github_issue_url=db_record.github_issue_url,
                duration_minutes=db_record.duration_minutes,
                estimated_completion_time=db_record.estimated_completion_time
            )
            
        except Exception as e:
            logger.error("Failed to retrieve session from database", 
                        session_id=session_id,
                        error=str(e))
            return None
        finally:
            db_session.close()
    
    def store_scoping_result(self, result: DevinScopeResult, 
                           relevant_files: List[str] = None,
                           file_analysis: str = None) -> bool:
        """Store scoping analysis results in the database."""
        try:
            db_session = db_manager.get_session()
            
            # Create database record
            db_record = ScopingResultDB(
                session_id=result.session_id,
                repository_name=result.repository_name,
                issue_number=result.issue_number,
                confidence_score=result.confidence_score,
                complexity_estimate=result.complexity_estimate,
                estimated_hours=result.estimated_hours,
                requirements_clarity=result.requirements_clarity,
                technical_feasibility=result.technical_feasibility,
                scope_completeness=result.scope_completeness,
                recommended_approach=result.recommended_approach,
                potential_challenges=result.potential_challenges,
                required_knowledge=result.required_knowledge,
                dependencies=result.dependencies,
                action_plan=result.action_plan,
                acceptance_criteria=result.acceptance_criteria,
                relevant_files=relevant_files or [],
                file_analysis=file_analysis,
                created_at=result.created_at,
                analysis_duration_minutes=result.analysis_duration_minutes
            )
            
            db_session.add(db_record)
            db_session.commit()
            
            logger.info("Scoping result stored in database", 
                       session_id=result.session_id,
                       repository=result.repository_name,
                       issue_number=result.issue_number)
            
            return True
            
        except Exception as e:
            logger.error("Failed to store scoping result in database", 
                        session_id=result.session_id,
                        error=str(e))
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def get_previous_scoping_summaries(self, repository_name: str, 
                                     limit: int = 5) -> List[Dict[str, Any]]:
        """Get previous scoping summaries for a repository."""
        try:
            db_session = db_manager.get_session()
            
            # Get recent scoping results for the repository
            results = db_session.query(ScopingResultDB).filter(
                ScopingResultDB.repository_name == repository_name
            ).order_by(desc(ScopingResultDB.created_at)).limit(limit).all()
            
            summaries = []
            for result in results:
                summary = {
                    "issue_number": result.issue_number,
                    "confidence_score": result.confidence_score,
                    "complexity_estimate": result.complexity_estimate,
                    "estimated_hours": result.estimated_hours,
                    "recommended_approach": result.recommended_approach,
                    "key_challenges": result.potential_challenges[:3] if result.potential_challenges else [],
                    "created_at": result.created_at.isoformat(),
                    "relevant_files": result.relevant_files[:5] if result.relevant_files else []
                }
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error("Failed to get previous scoping summaries", 
                        repository=repository_name,
                        error=str(e))
            return []
        finally:
            db_session.close()
    
    def store_repository_files(self, repository_name: str, 
                             files_data: List[Dict[str, Any]]) -> bool:
        """Store repository file structure and analysis."""
        try:
            db_session = db_manager.get_session()
            
            for file_data in files_data:
                db_record = RepositoryFileDB(
                    repository_name=repository_name,
                    file_path=file_data.get("path"),
                    file_type=file_data.get("type"),
                    file_size=file_data.get("size"),
                    last_modified=file_data.get("last_modified"),
                    language=file_data.get("language"),
                    complexity_score=file_data.get("complexity_score"),
                    importance_score=file_data.get("importance_score"),
                    description=file_data.get("description"),
                    related_issues=file_data.get("related_issues", [])
                )
                
                # Use merge to handle updates
                db_session.merge(db_record)
            
            db_session.commit()
            
            logger.info("Repository files stored in database", 
                       repository=repository_name,
                       file_count=len(files_data))
            
            return True
            
        except Exception as e:
            logger.error("Failed to store repository files", 
                        repository=repository_name,
                        error=str(e))
            db_session.rollback()
            return False
        finally:
            db_session.close()
    
    def get_relevant_files(self, repository_name: str, 
                          issue_keywords: List[str] = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get relevant files for an issue based on keywords and importance."""
        try:
            db_session = db_manager.get_session()
            
            query = db_session.query(RepositoryFileDB).filter(
                RepositoryFileDB.repository_name == repository_name
            )
            
            # Order by importance score and complexity
            query = query.order_by(
                desc(RepositoryFileDB.importance_score),
                desc(RepositoryFileDB.complexity_score)
            ).limit(limit)
            
            results = query.all()
            
            files = []
            for result in results:
                file_info = {
                    "path": result.file_path,
                    "type": result.file_type,
                    "language": result.language,
                    "importance_score": result.importance_score,
                    "complexity_score": result.complexity_score,
                    "description": result.description,
                    "related_issues": result.related_issues or []
                }
                files.append(file_info)
            
            return files
            
        except Exception as e:
            logger.error("Failed to get relevant files", 
                        repository=repository_name,
                        error=str(e))
            return []
        finally:
            db_session.close()
    
    def get_sessions_by_repository(self, repository_name: str,
                                 limit: int = 10) -> List[DevinSession]:
        """Get recent sessions for a repository."""
        try:
            db_session = db_manager.get_session()

            db_records = db_session.query(DevinSessionDB).filter(
                DevinSessionDB.repository_name == repository_name
            ).order_by(desc(DevinSessionDB.created_at)).limit(limit).all()

            sessions = []
            for db_record in db_records:
                session = DevinSession(
                    session_id=db_record.session_id,
                    status=DevinSessionStatus(db_record.status),
                    session_type=DevinSessionType(db_record.session_type),
                    created_at=db_record.created_at,
                    updated_at=db_record.updated_at,
                    completed_at=db_record.completed_at,
                    prompt=db_record.prompt,
                    repository_name=db_record.repository_name,
                    issue_number=db_record.issue_number,
                    tags=db_record.tags or [],
                    output=db_record.output,
                    error_message=db_record.error_message,
                    confidence_score=db_record.confidence_score,
                    session_url=db_record.session_url,
                    github_issue_url=db_record.github_issue_url,
                    duration_minutes=db_record.duration_minutes,
                    estimated_completion_time=db_record.estimated_completion_time
                )
                sessions.append(session)

            return sessions

        except Exception as e:
            logger.error("Failed to get sessions by repository",
                        repository=repository_name,
                        error=str(e))
            return []
        finally:
            db_session.close()

    def get_most_recent_session_for_issue(self, repository_name: str,
                                        issue_number: int) -> Optional[DevinSession]:
        """Get the most recent session for a specific issue."""
        try:
            db_session = db_manager.get_session()

            db_record = db_session.query(DevinSessionDB).filter(
                and_(
                    DevinSessionDB.repository_name == repository_name,
                    DevinSessionDB.issue_number == issue_number
                )
            ).order_by(desc(DevinSessionDB.created_at)).first()

            if not db_record:
                return None

            # Convert to Pydantic model
            session = DevinSession(
                session_id=db_record.session_id,
                status=DevinSessionStatus(db_record.status),
                session_type=DevinSessionType(db_record.session_type),
                created_at=db_record.created_at,
                updated_at=db_record.updated_at,
                completed_at=db_record.completed_at,
                prompt=db_record.prompt,
                repository_name=db_record.repository_name,
                issue_number=db_record.issue_number,
                tags=db_record.tags or [],
                output=db_record.output,
                error_message=db_record.error_message,
                confidence_score=db_record.confidence_score,
                session_url=db_record.session_url,
                github_issue_url=db_record.github_issue_url,
                duration_minutes=db_record.duration_minutes,
                estimated_completion_time=db_record.estimated_completion_time
            )

            return session

        except Exception as e:
            logger.error("Failed to get most recent session for issue",
                        repository=repository_name,
                        issue_number=issue_number,
                        error=str(e))
            return None
        finally:
            db_session.close()
