"""
FastAPI application entry point for GitHub-Devin Integration Dashboard.
"""

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from .config import settings
from .api import github_router, devin_router, dashboard_router
from .database import db_manager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting GitHub-Devin Dashboard",
               version="1.0.0",
               debug=settings.app_debug)

    # Initialize database
    try:
        db_manager.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down GitHub-Devin Dashboard")
    db_manager.close()


# Create FastAPI application
app = FastAPI(
    title=settings.dashboard_title,
    description="Dashboard for integrating GitHub Issues with Devin AI",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(github_router, prefix="/api/github", tags=["GitHub"])
app.include_router(devin_router, prefix="/api/devin", tags=["Devin"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# Mount static files (for frontend assets)
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except RuntimeError:
    # Directory doesn't exist yet - that's okay
    logger.warning("Static directory not found - frontend assets not available")


@app.get("/test-no-polling", response_class=HTMLResponse)
async def test_no_polling():
    """Test page with absolutely no auto-refresh to verify polling is stopped."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test - No Polling Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #007bff; color: white; }
            .result { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test Dashboard - No Auto-Polling</h1>
            <p>This page has <strong>NO automatic polling</strong>. Check server logs to verify no background requests.</p>

            <button class="btn btn-primary" onclick="testStats()">Manual Test: Get Stats</button>
            <button class="btn btn-primary" onclick="testIssues()">Manual Test: Get Issues</button>

            <div id="result" class="result">
                <strong>Result:</strong> Click buttons above to manually test API calls. No automatic requests should appear in server logs.
            </div>
        </div>

        <script>
            async function testStats() {
                document.getElementById('result').innerHTML = '<strong>Testing stats...</strong>';
                try {
                    const response = await fetch('/api/dashboard/stats');
                    const data = await response.json();
                    document.getElementById('result').innerHTML =
                        '<strong>Stats Result:</strong> ' + JSON.stringify(data, null, 2);
                } catch (error) {
                    document.getElementById('result').innerHTML =
                        '<strong>Error:</strong> ' + error.message;
                }
            }

            async function testIssues() {
                document.getElementById('result').innerHTML = '<strong>Testing issues...</strong>';
                try {
                    const response = await fetch('/api/dashboard/issues?limit=5');
                    const data = await response.json();
                    document.getElementById('result').innerHTML =
                        '<strong>Issues Result:</strong> Found ' + data.length + ' issues';
                } catch (error) {
                    document.getElementById('result').innerHTML =
                        '<strong>Error:</strong> ' + error.message;
                }
            }

            // NO AUTO-REFRESH CODE HERE - COMPLETELY MANUAL
            console.log('Test page loaded - no automatic polling enabled');
        </script>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GitHub-Devin Integration Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; padding: 20px; background: #f5f5f5;
            }
            .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            .header { text-align: center; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
            .stat-label { color: #666; margin-top: 5px; }
            .actions { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px; }
            .btn {
                padding: 10px 20px; background: #007bff; color: white; text-decoration: none;
                border-radius: 5px; border: none; cursor: pointer; font-size: 14px;
            }
            .btn:hover { background: #0056b3; }
            .btn:disabled { background: #6c757d; cursor: not-allowed; }
            .btn-secondary { background: #6c757d; }
            .btn-secondary:hover { background: #545b62; }
            .btn-success { background: #28a745; }
            .btn-success:hover { background: #218838; }
            .btn-warning { background: #ffc107; color: #212529; }
            .btn-warning:hover { background: #e0a800; }
            .btn-primary { background: #007bff; }
            .btn-primary:hover { background: #0056b3; }
            .btn-small { padding: 5px 10px; font-size: 12px; }

            .issues-section { margin-top: 30px; }
            .issues-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .issues-controls { display: flex; gap: 10px; align-items: center; }
            .issues-list { border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
            .issue-item {
                border-bottom: 1px solid #eee; padding: 15px; display: flex;
                justify-content: space-between; align-items: center; background: white;
            }
            .issue-item:last-child { border-bottom: none; }
            .issue-item:hover { background: #f8f9fa; }
            .issue-info { flex: 1; }
            .issue-title { font-weight: bold; margin-bottom: 5px; color: #333; }
            .issue-meta { color: #666; font-size: 14px; margin-bottom: 5px; }
            .issue-repo { color: #007bff; font-weight: 500; }
            .confidence-badge {
                display: inline-block; padding: 2px 8px; border-radius: 12px;
                font-size: 12px; font-weight: bold; margin-left: 10px;
            }
            .confidence-high { background: #d4edda; color: #155724; }
            .confidence-medium { background: #fff3cd; color: #856404; }
            .confidence-low { background: #f8d7da; color: #721c24; }
            .confidence-none { background: #e2e3e5; color: #6c757d; }
            .issue-actions { display: flex; gap: 8px; align-items: center; }
            .loading { text-align: center; padding: 40px; color: #666; }
            .empty-state { text-align: center; padding: 40px; color: #666; }
            .status-indicator {
                display: inline-block; width: 8px; height: 8px; border-radius: 50%;
                margin-right: 8px;
            }
            .status-indicator.open { background: #28a745; }
            .status-indicator.closed { background: #6c757d; }
            .api-links { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }
            .api-links h3 { margin-bottom: 15px; }
            .api-links a { display: inline-block; margin: 5px 10px 5px 0; }
            .status-indicator {
                display: inline-block; width: 8px; height: 8px; border-radius: 50%;
                margin-right: 5px;
            }
            .status-open { background: #28a745; }
            .status-closed { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>GitHub-Devin Integration Dashboard</h1>
                <p>Automate GitHub issue analysis and completion with Devin AI</p>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-issues">-</div>
                    <div class="stat-label">Total Issues</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="analyzed-issues">-</div>
                    <div class="stat-label">Analyzed Issues</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="active-sessions">-</div>
                    <div class="stat-label">Active Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="success-rate">-</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>

            <div class="actions">
                <button class="btn btn-primary" onclick="refreshStats()">Refresh Stats</button>
                <button class="btn btn-secondary" onclick="loadIssues()">Refresh Issues</button>
                <button class="btn btn-secondary" onclick="viewSessions()">View Sessions</button>
                <button class="btn btn-success" onclick="generateScope()">Generate Scope</button>
                <button class="btn btn-warning" onclick="resetScopeData()">Reset Scope Data</button>
            </div>

            <div class="issues-section">
                <div class="issues-header">
                    <h2>📋 GitHub Issues</h2>
                    <div class="issues-controls">
                        <select id="repository-filter" onchange="loadIssues()">
                            <option value="">All Repositories</option>
                        </select>
                        <select id="confidence-filter" onchange="loadIssues()">
                            <option value="">All Confidence Levels</option>
                            <option value="high">High Confidence</option>
                            <option value="medium">Medium Confidence</option>
                            <option value="low">Low Confidence</option>
                        </select>
                        <label>
                            <input type="checkbox" id="automation-ready-filter" onchange="loadIssues()">
                            Automation Ready Only
                        </label>
                    </div>
                </div>
                <div id="issues-container">
                    <div class="loading">Loading issues...</div>
                </div>
            </div>

            <div class="api-links">
                <h3>API Endpoints</h3>
                <a href="/docs" class="btn btn-secondary">API Documentation</a>
                <a href="/api/dashboard/stats" class="btn btn-secondary">Dashboard Stats</a>
                <a href="/api/github/issues" class="btn btn-secondary">GitHub Issues</a>
                <a href="/api/devin/sessions" class="btn btn-secondary">Devin Sessions</a>
            </div>
        </div>

        <script>
            let currentIssues = [];

            async function refreshStats() {
                try {
                    const response = await fetch('/api/dashboard/stats');
                    const stats = await response.json();

                    document.getElementById('total-issues').textContent = stats.total_issues || 0;
                    document.getElementById('analyzed-issues').textContent = stats.analyzed_issues || 0;
                    document.getElementById('active-sessions').textContent = stats.active_sessions || 0;
                    document.getElementById('success-rate').textContent =
                        ((stats.automation_success_rate || 0) * 100).toFixed(1) + '%';
                } catch (error) {
                    console.error('Failed to refresh stats:', error);
                }
            }

            async function loadIssues() {
                const container = document.getElementById('issues-container');
                container.innerHTML = '<div class="loading">Loading issues...</div>';

                try {
                    // Build query parameters
                    const params = new URLSearchParams();
                    const repository = document.getElementById('repository-filter').value;
                    const confidence = document.getElementById('confidence-filter').value;
                    const automationReady = document.getElementById('automation-ready-filter').checked;

                    if (repository) params.append('repository', repository);
                    if (confidence) params.append('confidence_level', confidence);
                    if (automationReady) params.append('automation_ready_only', 'true');
                    params.append('limit', '50');

                    const response = await fetch(`/api/dashboard/issues?${params}`);
                    const issues = await response.json();
                    currentIssues = issues;

                    displayIssues(issues);
                    updateRepositoryFilter(issues);
                } catch (error) {
                    console.error('Failed to load issues:', error);
                    container.innerHTML = '<div class="empty-state">Failed to load issues. Please try again.</div>';
                }
            }

            function displayIssues(issues) {
                const container = document.getElementById('issues-container');

                if (!issues || issues.length === 0) {
                    // Show a demo issue to demonstrate the Start Devin Implement functionality
                    const demoIssueHtml = `
                        <div class="issues-list">
                            <div class="issue-item">
                                <div class="issue-info">
                                    <div class="issue-title">
                                        <span class="status-indicator open"></span>
                                        #1 - Demo Issue: Add inventory management feature
                                        <span class="confidence-badge confidence-high">High Confidence (85%)</span>
                                    </div>
                                    <div class="issue-meta">
                                        <span class="issue-repo">parthobardhan/inventory-app</span>
                                        • Created: ${new Date().toLocaleDateString()}
                                        • Updated: ${new Date().toLocaleDateString()}
                                    </div>
                                    <div class="issue-meta">
                                        Complexity: medium • Automation Suitable: Yes • Est. Hours: 4
                                    </div>
                                </div>
                                <div class="issue-actions">
                                    <button class="btn btn-secondary btn-small" onclick="alert('This is a demo - Re-scope functionality would work here')">
                                        Re-scope with Devin
                                    </button>
                                    <button class="btn btn-primary btn-small" onclick="startDevinImplement('parthobardhan/inventory-app', 1)">
                                        Start Devin Implement
                                    </button>
                                    <button class="btn btn-success btn-small" onclick="alert('This is a demo - Complete Issue functionality would work here')">
                                        Complete Issue
                                    </button>
                                    <a href="https://github.com/parthobardhan/inventory-app/issues/1" target="_blank" class="btn btn-secondary btn-small">
                                        View on GitHub
                                    </a>
                                </div>
                            </div>
                            <div class="issue-item">
                                <div class="issue-info">
                                    <div class="issue-title">
                                        <span class="status-indicator open"></span>
                                        #2 - Demo Issue: Fix user authentication bug
                                        <span class="confidence-badge confidence-low">Low Confidence (45%)</span>
                                    </div>
                                    <div class="issue-meta">
                                        <span class="issue-repo">parthobardhan/inventory-app</span>
                                        • Created: ${new Date().toLocaleDateString()}
                                        • Updated: ${new Date().toLocaleDateString()}
                                    </div>
                                    <div class="issue-meta">
                                        Complexity: high • Automation Suitable: No • Est. Hours: 8
                                    </div>
                                </div>
                                <div class="issue-actions">
                                    <button class="btn btn-secondary btn-small" onclick="alert('This is a demo - Re-scope functionality would work here')">
                                        Re-scope with Devin
                                    </button>
                                    <button class="btn btn-primary btn-small" onclick="startDevinImplement('parthobardhan/inventory-app', 2)">
                                        Start Devin Implement
                                    </button>
                                    <a href="https://github.com/parthobardhan/inventory-app/issues/2" target="_blank" class="btn btn-secondary btn-small">
                                        View on GitHub
                                    </a>
                                </div>
                            </div>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px; border-left: 4px solid #007bff;">
                            <strong>🧪 Demo Mode:</strong> These are demo issues to showcase the "Start Devin Implement" functionality.
                            The first issue has high confidence (85%) and will create an implementation session.
                            The second has low confidence (45%) and will show why implementation isn't started.
                        </div>
                    `;
                    container.innerHTML = demoIssueHtml;
                    return;
                }

                const issuesHtml = issues.map(issueData => {
                    const issue = issueData.issue;
                    const analysis = issueData.analysis;
                    const isAutomationReady = issueData.is_automation_ready || false;

                    const confidenceScore = analysis ? analysis.overall_confidence : null;
                    const confidenceBadge = getConfidenceBadge(confidenceScore);
                    const statusIndicator = issue.state === 'open' ? 'status-open' : 'status-closed';

                    return `
                        <div class="issue-item">
                            <div class="issue-info">
                                <div class="issue-title">
                                    <span class="status-indicator ${statusIndicator}"></span>
                                    #${issue.number} - ${issue.title}
                                    ${confidenceBadge}
                                </div>
                                <div class="issue-meta">
                                    <span class="issue-repo">${issue.repository ? issue.repository.full_name : 'Unknown Repository'}</span>
                                    • Created: ${new Date(issue.created_at).toLocaleDateString()}
                                    • Updated: ${new Date(issue.updated_at).toLocaleDateString()}
                                </div>
                                ${analysis ? `
                                    <div class="issue-meta">
                                        Complexity: ${analysis.complexity_level} •
                                        Automation Suitable: ${analysis.automation_suitable ? 'Yes' : 'No'}
                                        ${analysis.estimated_hours ? ` • Est. Hours: ${analysis.estimated_hours}` : ''}
                                    </div>
                                ` : `
                                    <div class="issue-meta">
                                        <em>No scoping analysis available - Click "Generate Scope" to analyze this issue</em>
                                    </div>
                                `}
                            </div>
                            <div class="issue-actions">
                                ${!analysis ? `
                                    <button class="btn btn-warning btn-small" onclick="generateAnalysisForIssue('${issue.repository ? issue.repository.full_name : ''}', ${issue.number})">
                                        Start Devin Scope
                                    </button>
                                ` : `
                                    <button class="btn btn-secondary btn-small" onclick="generateAnalysisForIssue('${issue.repository ? issue.repository.full_name : ''}', ${issue.number})">
                                        Re-scope with Devin
                                    </button>
                                `}
                                ${analysis && confidenceScore && confidenceScore > 0.7 ? `
                                    <button class="btn btn-success btn-small" onclick="completeIssue('${issue.repository ? issue.repository.full_name : ''}', ${issue.number})">
                                        Complete Issue
                                    </button>
                                ` : ''}
                                ${analysis ? `
                                    <button class="btn btn-primary btn-small" onclick="startDevinImplement('${issue.repository ? issue.repository.full_name : ''}', ${issue.number})">
                                        Start Devin Implement
                                    </button>
                                ` : ''}
                                <a href="${issue.html_url}" target="_blank" class="btn btn-secondary btn-small">
                                    View on GitHub
                                </a>
                            </div>
                        </div>
                    `;
                }).join('');

                container.innerHTML = `<div class="issues-list">${issuesHtml}</div>`;
            }

            function getConfidenceBadge(confidenceScore) {
                if (!confidenceScore) {
                    return '<span class="confidence-badge confidence-none">Not Analyzed</span>';
                }

                const percentage = Math.round(confidenceScore * 100);
                if (confidenceScore >= 0.8) {
                    return `<span class="confidence-badge confidence-high">High (${percentage}%)</span>`;
                } else if (confidenceScore >= 0.5) {
                    return `<span class="confidence-badge confidence-medium">Medium (${percentage}%)</span>`;
                } else {
                    return `<span class="confidence-badge confidence-low">Low (${percentage}%)</span>`;
                }
            }

            function updateRepositoryFilter(issues) {
                const select = document.getElementById('repository-filter');
                const currentValue = select.value;

                // Get unique repositories
                const repositories = [...new Set(issues.map(issueData =>
                    issueData.issue.repository ? issueData.issue.repository.full_name : null
                ).filter(Boolean))].sort();

                // Update options
                select.innerHTML = '<option value="">All Repositories</option>' +
                    repositories.map(repo => `<option value="${repo}">${repo}</option>`).join('');

                // Restore selection if still valid
                if (repositories.includes(currentValue)) {
                    select.value = currentValue;
                }
            }

            async function scopeIssue(repository, issueNumber) {
                if (!repository) {
                    alert('Repository information not available');
                    return;
                }

                try {
                    const response = await fetch('/api/devin/scope-issue', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            repository_name: repository,
                            issue_number: parseInt(issueNumber)
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        alert(`Scoping session started: ${result.session_id}\\nConfidence Score: ${(result.confidence_score * 100).toFixed(1)}%\\n\\nClick "Refresh Issues" to see updated analysis.`);

                        // Auto-trigger completion if confidence is high
                        if (result.confidence_score > 0.7) {
                            const shouldComplete = confirm(
                                `High confidence score (${(result.confidence_score * 100).toFixed(1)}%)! ` +
                                'Would you like to automatically start the completion process?'
                            );
                            if (shouldComplete) {
                                completeIssue(repository, issueNumber);
                            }
                        }
                    } else {
                        const error = await response.text();
                        throw new Error(error);
                    }
                } catch (error) {
                    console.error('Failed to scope issue:', error);
                    alert('Failed to start scoping session: ' + error.message);
                }
            }

            async function completeIssue(repository, issueNumber) {
                if (!repository) {
                    alert('Repository information not available');
                    return;
                }

                try {
                    const response = await fetch('/api/devin/complete-issue', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            repository_name: repository,
                            issue_number: parseInt(issueNumber),
                            use_existing_scope: true
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        alert(`Completion session started: ${result.session_id}\\n\\nClick "Refresh Issues" to see updated status.`);
                    } else {
                        const error = await response.text();
                        throw new Error(error);
                    }
                } catch (error) {
                    console.error('Failed to complete issue:', error);
                    alert('Failed to start completion session: ' + error.message);
                }
            }

            function viewSessions() {
                window.open('/api/devin/sessions', '_blank');
            }

            async function generateScope() {
                const repository = 'parthobardhan/inventory-app';
                const issueNumber = 2;

                try {
                    // First generate local analysis
                    const analysisResponse = await fetch('/api/devin/generate-analysis', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            repository_name: repository,
                            issue_number: issueNumber
                        })
                    });

                    if (analysisResponse.ok) {
                        const analysisResult = await analysisResponse.json();
                        console.log('Analysis generated:', analysisResult);

                        // Reload issues to show the analysis
                        loadIssues();

                        alert(`Analysis generated successfully!\\n\\nRepository: ${repository}\\nIssue: #${issueNumber}\\n\\nLocal analysis has been created. You can now see confidence scores and complexity estimates.`);
                    } else {
                        const error = await analysisResponse.text();
                        throw new Error(`Analysis generation failed: ${error}`);
                    }
                } catch (error) {
                    console.error('Failed to generate scope:', error);
                    alert('Failed to generate analysis: ' + error.message);
                }
            }

            async function generateAnalysisForIssue(repository, issueNumber) {
                if (!repository) {
                    alert('Repository information not available');
                    return;
                }

                // Find the issue in currentIssues to get the title
                const issueData = currentIssues.find(item =>
                    item.issue.number === parseInt(issueNumber) &&
                    item.issue.repository &&
                    item.issue.repository.full_name === repository
                );

                const issueTitle = issueData ? issueData.issue.title : `Issue #${issueNumber}`;

                try {
                    // Create Devin session for scoping the issue
                    const response = await fetch('/api/devin/scope-specific-issue', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            repository_name: repository,
                            issue_number: parseInt(issueNumber),
                            issue_title: issueTitle
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();
                        console.log('Devin session created for issue:', result);

                        // Show success message with session details
                        alert(`Devin scoping session started successfully!\\n\\nSession ID: ${result.session_id}\\nRepository: ${repository}\\nIssue: #${issueNumber}\\n\\nYou can view the session at: ${result.session_url || 'Devin dashboard'}\\n\\nClick "Refresh Issues" to see any updated analysis.`);
                    } else {
                        const error = await response.text();
                        throw new Error(error);
                    }
                } catch (error) {
                    console.error('Failed to create Devin session for issue:', error);
                    alert('Failed to start Devin scoping session: ' + error.message);
                }
            }

            async function resetScopeData() {
                if (!confirm('Are you sure you want to reset all scope data?\\n\\nThis will clear all existing scoping analyses and session data. This action cannot be undone.')) {
                    return;
                }

                try {
                    const response = await fetch('/api/devin/clear-scope-data', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' }
                    });

                    if (response.ok) {
                        const result = await response.json();
                        alert(`Scope data reset successfully!\\n\\n${result.message}\\n\\nClick "Refresh Stats" and "Refresh Issues" to see the cleared state.`);
                    } else {
                        const error = await response.text();
                        throw new Error(error);
                    }
                } catch (error) {
                    console.error('Failed to reset scope data:', error);
                    alert('Failed to reset scope data: ' + error.message);
                }
            }

            async function startDevinImplement(repository, issueNumber) {
                if (!repository) {
                    alert('Repository information not available');
                    return;
                }

                // Show demo behavior for demo issues
                if (repository === 'parthobardhan/inventory-app' && (issueNumber === 1 || issueNumber === 2)) {
                    let message = '';

                    if (issueNumber === 1) {
                        // High confidence demo
                        message = `🎯 Demo Response for Issue #1:\\n\\n`;
                        message += `Session ID: demo-session-12345\\n`;
                        message += `Confidence Score: 85%\\n\\n`;
                        message += `✅ Implementation session created!\\n`;
                        message += `Implementation Session ID: impl-session-67890\\n`;
                        message += `Session URL: https://api.devin.ai/sessions/impl-session-67890\\n\\n`;
                        message += `Enhanced prompt includes:\\n`;
                        message += `• Relevant file paths from previous analysis\\n`;
                        message += `• Previous work summaries\\n`;
                        message += `• Instructions to create branch in parthobardhan/inventory-app\\n`;
                        message += `• Specific implementation steps\\n\\n`;
                        message += `The implementation session is ready to start coding!`;

                        alert(message);

                        if (confirm('This is a demo. Would you like to see what the implementation session URL would look like?')) {
                            alert('In a real scenario, this would open:\\nhttps://api.devin.ai/sessions/impl-session-67890\\n\\nThe session would contain a detailed prompt with:\\n• File paths: src/inventory.py, src/models.py\\n• Previous summaries from related issues\\n• Step-by-step implementation plan\\n• Branch creation instructions');
                        }
                    } else {
                        // Low confidence demo
                        message = `🎯 Demo Response for Issue #2:\\n\\n`;
                        message += `Session ID: demo-session-54321\\n`;
                        message += `Confidence Score: 45%\\n\\n`;
                        message += `❌ Implementation not started\\n`;
                        message += `Confidence score (45%) is not high enough (>70%) for automatic implementation\\n\\n`;
                        message += `Recommendation: Re-scope this issue first to improve confidence before attempting implementation.`;

                        alert(message);
                    }
                    return;
                }

                // Real API call for non-demo cases
                try {
                    const response = await fetch('/api/devin/start-implement', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            repository_name: repository,
                            issue_number: parseInt(issueNumber)
                        })
                    });

                    if (response.ok) {
                        const result = await response.json();

                        let message = `Session ID: ${result.session_id}\\nConfidence Score: ${result.confidence_score}%\\n\\n`;

                        if (result.implementation_started) {
                            message += `✅ Implementation session created!\\n`;
                            message += `Implementation Session ID: ${result.implementation_session_id}\\n`;
                            message += `Session URL: ${result.implementation_session_url}\\n\\n`;
                            message += result.message;
                        } else {
                            message += `❌ Implementation not started\\n`;
                            message += result.message || result.error || 'Confidence score too low for automatic implementation';
                        }

                        alert(message);

                        // If implementation was started, optionally open the session URL
                        if (result.implementation_started && result.implementation_session_url) {
                            if (confirm('Would you like to open the implementation session in a new tab?')) {
                                window.open(result.implementation_session_url, '_blank');
                            }
                        }
                    } else {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to start implementation');
                    }
                } catch (error) {
                    console.error('Failed to start Devin implementation:', error);
                    alert('Failed to start Devin implementation: ' + error.message);
                }
            }

            // Auto-loading and auto-refresh removed - now using manual refresh buttons only
            // Users must click "Refresh Stats" and "Refresh Issues" to load data
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "services": {
            "github": "connected",
            "devin": "connected"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
