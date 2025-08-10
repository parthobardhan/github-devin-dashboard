"""
Issue analysis service for generating confidence scores and complexity assessments.
"""

import re
import math
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
import structlog

from ..models.github_models import GitHubIssue, GitHubLabel
from ..models.dashboard_models import (
    IssueAnalysis, ComplexityLevel, ConfidenceLevel, IssueWithAnalysis
)

logger = structlog.get_logger(__name__)


class AnalysisService:
    """Service for analyzing GitHub issues and generating confidence scores."""
    
    def __init__(self):
        """Initialize analysis service with scoring weights and patterns."""
        
        # Scoring weights for different factors
        self.weights = {
            'requirements_clarity': 0.25,
            'technical_feasibility': 0.25,
            'scope_completeness': 0.25,
            'context_availability': 0.25
        }
        
        # Keywords that indicate different complexity levels
        self.complexity_keywords = {
            'low': {
                'bug', 'fix', 'typo', 'documentation', 'readme', 'comment',
                'style', 'formatting', 'lint', 'minor', 'simple', 'small'
            },
            'medium': {
                'feature', 'enhancement', 'improvement', 'refactor', 'update',
                'modify', 'change', 'add', 'implement', 'create'
            },
            'high': {
                'architecture', 'migration', 'breaking', 'major', 'complex',
                'integration', 'security', 'performance', 'scalability',
                'database', 'api', 'framework', 'redesign', 'rewrite'
            }
        }
        
        # Technical feasibility indicators
        self.feasibility_indicators = {
            'high': {
                'clear steps', 'well defined', 'specific', 'detailed',
                'reproduction steps', 'expected behavior', 'actual behavior'
            },
            'medium': {
                'feature request', 'enhancement', 'improvement', 'should'
            },
            'low': {
                'vague', 'unclear', 'maybe', 'possibly', 'investigate',
                'research', 'explore', 'consider', 'discuss'
            }
        }
        
        # Labels that affect confidence scoring
        self.label_modifiers = {
            'bug': 0.1,           # Bugs are often clearer to fix
            'documentation': 0.15, # Documentation is usually straightforward
            'good first issue': 0.2, # Explicitly marked as beginner-friendly
            'help wanted': 0.1,    # Community wants help
            'enhancement': 0.0,    # Neutral
            'feature': -0.05,      # Features can be more complex
            'breaking change': -0.2, # Breaking changes are risky
            'needs investigation': -0.15, # Unclear scope
            'wontfix': -1.0,       # Should not be automated
            'duplicate': -1.0,     # Should not be automated
            'invalid': -1.0        # Should not be automated
        }
    
    def analyze_issue(self, issue: GitHubIssue) -> IssueAnalysis:
        """
        Perform comprehensive analysis of a GitHub issue.
        
        Args:
            issue: GitHub issue to analyze
            
        Returns:
            IssueAnalysis with confidence scores and recommendations
        """
        try:
            logger.info("Analyzing issue", 
                       issue_number=issue.number,
                       repository=issue.repository.full_name if issue.repository else "unknown")
            
            # Calculate individual scoring factors
            requirements_clarity = self._assess_requirements_clarity(issue)
            technical_feasibility = self._assess_technical_feasibility(issue)
            scope_completeness = self._assess_scope_completeness(issue)
            context_availability = self._assess_context_availability(issue)
            
            # Calculate overall confidence score
            overall_confidence = (
                requirements_clarity * self.weights['requirements_clarity'] +
                technical_feasibility * self.weights['technical_feasibility'] +
                scope_completeness * self.weights['scope_completeness'] +
                context_availability * self.weights['context_availability']
            )
            
            # Apply label modifiers
            label_modifier = self._calculate_label_modifier(issue.labels)
            overall_confidence = max(0.0, min(1.0, overall_confidence + label_modifier))
            
            # Determine confidence level
            confidence_level = self._get_confidence_level(overall_confidence)
            
            # Assess complexity
            complexity_score, complexity_level = self._assess_complexity(issue)
            
            # Estimate hours based on complexity and confidence
            estimated_hours = self._estimate_hours(complexity_level, overall_confidence)
            
            # Generate key factors and challenges
            key_factors = self._identify_key_factors(issue, overall_confidence)
            potential_challenges = self._identify_challenges(issue, complexity_level)
            
            # Determine recommended action
            recommended_action = self._get_recommended_action(
                overall_confidence, complexity_level
            )
            
            # Check if suitable for automation
            automation_suitable = self._is_automation_suitable(
                issue, overall_confidence, complexity_level
            )
            
            analysis = IssueAnalysis(
                issue_id=issue.id,
                issue_number=issue.number,
                repository_name=issue.repository.full_name if issue.repository else "unknown",
                overall_confidence=overall_confidence,
                confidence_level=confidence_level,
                complexity_score=complexity_score,
                complexity_level=complexity_level,
                estimated_hours=estimated_hours,
                requirements_clarity=requirements_clarity,
                technical_feasibility=technical_feasibility,
                scope_completeness=scope_completeness,
                context_availability=context_availability,
                key_factors=key_factors,
                potential_challenges=potential_challenges,
                recommended_action=recommended_action,
                automation_suitable=automation_suitable
            )
            
            logger.info("Issue analysis completed",
                       issue_number=issue.number,
                       confidence=overall_confidence,
                       complexity=complexity_level,
                       automation_suitable=automation_suitable)
            
            return analysis
            
        except Exception as e:
            logger.error("Failed to analyze issue", 
                        issue_number=issue.number, 
                        error=str(e))
            
            # Return default analysis on error
            return IssueAnalysis(
                issue_id=issue.id,
                issue_number=issue.number,
                repository_name=issue.repository.full_name if issue.repository else "unknown",
                overall_confidence=0.3,
                confidence_level=ConfidenceLevel.LOW,
                complexity_score=0.5,
                complexity_level=ComplexityLevel.UNKNOWN,
                requirements_clarity=0.3,
                technical_feasibility=0.3,
                scope_completeness=0.3,
                context_availability=0.3,
                key_factors=["Analysis failed"],
                potential_challenges=["Unable to analyze issue"],
                recommended_action="Manual review required",
                automation_suitable=False
            )
    
    def _assess_requirements_clarity(self, issue: GitHubIssue) -> float:
        """Assess how clear the requirements are."""
        score = 0.0
        text = f"{issue.title} {issue.body or ''}".lower()
        
        # Check for clear problem description
        if any(phrase in text for phrase in [
            'expected', 'actual', 'should', 'when', 'then', 'given'
        ]):
            score += 0.3
        
        # Check for reproduction steps
        if any(phrase in text for phrase in [
            'steps to reproduce', 'how to reproduce', 'reproduction',
            'step 1', 'step 2', '1.', '2.', '3.'
        ]):
            score += 0.3
        
        # Check for specific details
        if len(text) > 100:  # Reasonable description length
            score += 0.2
        
        # Check for code examples or error messages
        if '```' in (issue.body or '') or 'error' in text:
            score += 0.2
        
        # Penalty for vague language
        vague_words = ['maybe', 'possibly', 'might', 'unclear', 'investigate']
        vague_count = sum(1 for word in vague_words if word in text)
        score -= vague_count * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _assess_technical_feasibility(self, issue: GitHubIssue) -> float:
        """Assess technical feasibility of the issue."""
        score = 0.5  # Start with neutral score
        text = f"{issue.title} {issue.body or ''}".lower()
        
        # Check for high feasibility indicators
        for indicator in self.feasibility_indicators['high']:
            if indicator in text:
                score += 0.15
        
        # Check for medium feasibility indicators
        for indicator in self.feasibility_indicators['medium']:
            if indicator in text:
                score += 0.05
        
        # Check for low feasibility indicators
        for indicator in self.feasibility_indicators['low']:
            if indicator in text:
                score -= 0.15
        
        # Bonus for bug reports (usually more feasible)
        if any(label.name.lower() == 'bug' for label in issue.labels):
            score += 0.2
        
        # Penalty for research/investigation tasks
        if any(word in text for word in ['research', 'investigate', 'explore']):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _assess_scope_completeness(self, issue: GitHubIssue) -> float:
        """Assess how complete the scope definition is."""
        score = 0.0
        text = f"{issue.title} {issue.body or ''}".lower()
        
        # Check for acceptance criteria
        if any(phrase in text for phrase in [
            'acceptance criteria', 'definition of done', 'requirements',
            'must', 'should', 'shall'
        ]):
            score += 0.3
        
        # Check for specific deliverables
        if any(phrase in text for phrase in [
            'deliverable', 'output', 'result', 'outcome'
        ]):
            score += 0.2
        
        # Check for constraints or limitations
        if any(phrase in text for phrase in [
            'constraint', 'limitation', 'requirement', 'must not'
        ]):
            score += 0.2
        
        # Check for context about why this is needed
        if any(phrase in text for phrase in [
            'because', 'reason', 'purpose', 'goal', 'objective'
        ]):
            score += 0.2
        
        # Bonus for detailed descriptions
        if len(issue.body or '') > 200:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _assess_context_availability(self, issue: GitHubIssue) -> float:
        """Assess how much context is available."""
        score = 0.0
        
        # Repository information available
        if issue.repository:
            score += 0.2
        
        # Labels provide context
        if issue.labels:
            score += min(0.3, len(issue.labels) * 0.1)
        
        # Assignees indicate ownership
        if issue.assignees:
            score += 0.1
        
        # Comments provide additional context
        if issue.comments > 0:
            score += min(0.2, issue.comments * 0.05)
        
        # Milestone provides project context
        if issue.milestone:
            score += 0.1
        
        # Recent activity indicates relevance
        days_old = (datetime.now() - issue.updated_at).days
        if days_old < 7:
            score += 0.1
        elif days_old < 30:
            score += 0.05
        
        return max(0.0, min(1.0, score))

    def _assess_complexity(self, issue: GitHubIssue) -> Tuple[float, ComplexityLevel]:
        """Assess the complexity of the issue."""
        text = f"{issue.title} {issue.body or ''}".lower()

        # Count keywords for each complexity level
        low_count = sum(1 for keyword in self.complexity_keywords['low'] if keyword in text)
        medium_count = sum(1 for keyword in self.complexity_keywords['medium'] if keyword in text)
        high_count = sum(1 for keyword in self.complexity_keywords['high'] if keyword in text)

        # Calculate complexity score
        total_keywords = low_count + medium_count + high_count
        if total_keywords == 0:
            complexity_score = 0.5  # Default medium complexity
            complexity_level = ComplexityLevel.MEDIUM
        else:
            # Weighted average
            complexity_score = (
                (low_count * 0.2) +
                (medium_count * 0.5) +
                (high_count * 0.8)
            ) / total_keywords

            # Determine level
            if complexity_score < 0.35:
                complexity_level = ComplexityLevel.LOW
            elif complexity_score < 0.65:
                complexity_level = ComplexityLevel.MEDIUM
            else:
                complexity_level = ComplexityLevel.HIGH

        # Adjust based on issue length (longer descriptions often mean more complexity)
        description_length = len(issue.body or '')
        if description_length > 1000:
            complexity_score = min(1.0, complexity_score + 0.1)
        elif description_length < 100:
            complexity_score = max(0.0, complexity_score - 0.1)

        return complexity_score, complexity_level

    def _calculate_label_modifier(self, labels: List[GitHubLabel]) -> float:
        """Calculate confidence modifier based on labels."""
        modifier = 0.0

        for label in labels:
            label_name = label.name.lower()
            for pattern, value in self.label_modifiers.items():
                if pattern in label_name:
                    modifier += value
                    break

        return max(-0.5, min(0.3, modifier))  # Cap the modifier

    def _get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level."""
        if confidence_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _estimate_hours(self, complexity: ComplexityLevel, confidence: float) -> Optional[float]:
        """Estimate hours required based on complexity and confidence."""
        base_hours = {
            ComplexityLevel.LOW: 2.0,
            ComplexityLevel.MEDIUM: 8.0,
            ComplexityLevel.HIGH: 24.0,
            ComplexityLevel.UNKNOWN: 8.0
        }

        hours = base_hours[complexity]

        # Adjust based on confidence (lower confidence = more time needed)
        confidence_multiplier = 1.0 + (1.0 - confidence) * 0.5
        hours *= confidence_multiplier

        return round(hours, 1)

    def _identify_key_factors(self, issue: GitHubIssue, confidence: float) -> List[str]:
        """Identify key factors affecting the analysis."""
        factors = []
        text = f"{issue.title} {issue.body or ''}".lower()

        if confidence >= 0.8:
            factors.append("High confidence - well-defined requirements")
        elif confidence <= 0.3:
            factors.append("Low confidence - unclear requirements")

        if 'bug' in [label.name.lower() for label in issue.labels]:
            factors.append("Bug report - typically more straightforward")

        if issue.comments > 5:
            factors.append("Active discussion - good community engagement")

        if any(word in text for word in ['urgent', 'critical', 'blocker']):
            factors.append("High priority issue")

        if len(issue.body or '') > 500:
            factors.append("Detailed description provided")

        if issue.assignees:
            factors.append("Has assigned developers")

        return factors

    def _identify_challenges(self, issue: GitHubIssue, complexity: ComplexityLevel) -> List[str]:
        """Identify potential challenges for automation."""
        challenges = []
        text = f"{issue.title} {issue.body or ''}".lower()

        if complexity == ComplexityLevel.HIGH:
            challenges.append("High complexity may require human oversight")

        if any(word in text for word in ['breaking', 'migration', 'architecture']):
            challenges.append("May involve breaking changes or architectural decisions")

        if any(word in text for word in ['ui', 'ux', 'design', 'visual']):
            challenges.append("UI/UX changes may require design input")

        if any(word in text for word in ['security', 'auth', 'permission']):
            challenges.append("Security implications require careful review")

        if any(word in text for word in ['performance', 'optimization', 'scale']):
            challenges.append("Performance considerations may need benchmarking")

        if not issue.body or len(issue.body) < 50:
            challenges.append("Limited description may require clarification")

        if issue.comments == 0:
            challenges.append("No community discussion or feedback")

        return challenges

    def _get_recommended_action(self, confidence: float, complexity: ComplexityLevel) -> str:
        """Get recommended action based on analysis."""
        if confidence >= 0.8 and complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM]:
            return "Suitable for automated completion"
        elif confidence >= 0.6:
            return "Consider automated scoping with human review"
        elif confidence >= 0.4:
            return "Requires human analysis before automation"
        else:
            return "Manual handling recommended - unclear requirements"

    def _is_automation_suitable(
        self,
        issue: GitHubIssue,
        confidence: float,
        complexity: ComplexityLevel
    ) -> bool:
        """Determine if issue is suitable for automation."""

        # Check for blocking labels
        blocking_labels = {'wontfix', 'duplicate', 'invalid', 'question'}
        if any(label.name.lower() in blocking_labels for label in issue.labels):
            return False

        # Minimum confidence threshold
        if confidence < 0.5:
            return False

        # Very high complexity issues need human oversight
        if complexity == ComplexityLevel.HIGH and confidence < 0.8:
            return False

        # Check for automation-friendly indicators
        text = f"{issue.title} {issue.body or ''}".lower()

        # Issues requiring human judgment
        human_judgment_keywords = [
            'design decision', 'architecture decision', 'should we',
            'what do you think', 'opinion', 'preference', 'strategy'
        ]

        if any(keyword in text for keyword in human_judgment_keywords):
            return False

        return True

    def create_issue_with_analysis(self, issue: GitHubIssue) -> IssueWithAnalysis:
        """Create an IssueWithAnalysis object."""
        analysis = self.analyze_issue(issue)
        return IssueWithAnalysis(
            issue=issue,
            analysis=analysis,
            active_sessions=[]  # Will be populated by session service
        )
