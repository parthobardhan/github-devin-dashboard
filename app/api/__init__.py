"""
API endpoints for the GitHub-Devin Dashboard application.
"""

from .github_routes import router as github_router
from .devin_routes import router as devin_router
from .dashboard_routes import router as dashboard_router

__all__ = [
    "github_router",
    "devin_router",
    "dashboard_router"
]
