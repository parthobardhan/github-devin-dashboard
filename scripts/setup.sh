#!/bin/bash

# GitHub-Devin Dashboard Setup Script
# This script sets up the development environment for the dashboard

set -e  # Exit on any error

echo "Setting up GitHub-Devin Integration Dashboard..."

# Check if Python 3.8+ is available
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and configuration"
else
    echo ".env file already exists"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p app/static/css
mkdir -p app/static/js
mkdir -p app/static/templates
mkdir -p logs
mkdir -p data

# Create a simple CSS file
cat > app/static/css/dashboard.css << 'EOF'
/* GitHub-Devin Dashboard Styles */
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --danger-color: #dc3545;
    --light-color: #f8f9fa;
    --dark-color: #343a40;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 0;
    background-color: var(--light-color);
    color: var(--dark-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}

.stat-value {
    font-size: 2.5em;
    font-weight: bold;
    color: var(--primary-color);
    margin-bottom: 10px;
}

.stat-label {
    color: var(--secondary-color);
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.btn {
    display: inline-block;
    padding: 10px 20px;
    background: var(--primary-color);
    color: white;
    text-decoration: none;
    border-radius: 5px;
    border: none;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.2s;
}

.btn:hover {
    background: #0056b3;
}

.btn-secondary {
    background: var(--secondary-color);
}

.btn-secondary:hover {
    background: #545b62;
}

.issue-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid var(--primary-color);
}

.confidence-high { border-left-color: var(--success-color); }
.confidence-medium { border-left-color: var(--warning-color); }
.confidence-low { border-left-color: var(--danger-color); }

.loading {
    text-align: center;
    padding: 40px;
    color: var(--secondary-color);
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
}
EOF

echo "Created basic CSS styles"

# Create a simple JavaScript file
cat > app/static/js/dashboard.js << 'EOF'
// GitHub-Devin Dashboard JavaScript

class Dashboard {
    constructor() {
        this.apiBase = '/api';
        this.refreshInterval = 30000; // 30 seconds
        this.init();
    }

    init() {
        this.loadStats();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    async loadStats() {
        try {
            const response = await fetch(`${this.apiBase}/dashboard/stats`);
            const stats = await response.json();
            this.updateStatsDisplay(stats);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        const elements = {
            'total-issues': stats.total_issues || 0,
            'analyzed-issues': stats.analyzed_issues || 0,
            'active-sessions': stats.active_sessions || 0,
            'success-rate': ((stats.automation_success_rate || 0) * 100).toFixed(1) + '%'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    setupEventListeners() {
        // Add event listeners for buttons and interactions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action]')) {
                const action = e.target.dataset.action;
                this.handleAction(action, e.target);
            }
        });
    }

    handleAction(action, element) {
        switch (action) {
            case 'refresh-stats':
                this.loadStats();
                break;
            case 'scope-issue':
                this.scopeIssue(element.dataset.repo, element.dataset.issue);
                break;
            case 'complete-issue':
                this.completeIssue(element.dataset.repo, element.dataset.issue);
                break;
        }
    }

    async scopeIssue(repo, issueNumber) {
        try {
            const response = await fetch(`${this.apiBase}/devin/scope-issue`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repository_name: repo,
                    issue_number: parseInt(issueNumber)
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Scoping session started: ${result.session_id}`);
            } else {
                throw new Error('Failed to start scoping session');
            }
        } catch (error) {
            console.error('Failed to scope issue:', error);
            alert('Failed to start scoping session');
        }
    }

    async completeIssue(repo, issueNumber) {
        try {
            const response = await fetch(`${this.apiBase}/devin/complete-issue`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    repository_name: repo,
                    issue_number: parseInt(issueNumber)
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Completion session started: ${result.session_id}`);
            } else {
                throw new Error('Failed to start completion session');
            }
        } catch (error) {
            console.error('Failed to complete issue:', error);
            alert('Failed to start completion session');
        }
    }

    startAutoRefresh() {
        setInterval(() => {
            this.loadStats();
        }, this.refreshInterval);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
EOF

echo "Created dashboard JavaScript"

# Run basic tests to ensure everything is working
echo "Running basic tests..."
python3 -c "
import sys
sys.path.append('.')
try:
    from app.config import settings
    print('Configuration loaded successfully')
except Exception as e:
    print(f'Configuration error: {e}')
    sys.exit(1)

try:
    from app.models.github_models import GitHubIssue
    from app.models.devin_models import DevinSession
    from app.models.dashboard_models import DashboardStats
    print('Models imported successfully')
except Exception as e:
    print(f'Model import error: {e}')
    sys.exit(1)
"

echo ""
echo "Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - GITHUB_TOKEN: Your GitHub personal access token"
echo "   - DEVIN_API_KEY: Your Devin API key"
echo "   - GITHUB_REPOS: Comma-separated list of repositories (owner/repo)"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Start the application:"
echo "   python -m app.main"
echo "   # or"
echo "   uvicorn app.main:app --reload"
echo ""
echo "4. Open your browser to:"
echo "   http://localhost:8000"
echo ""
echo "5. API documentation available at:"
echo "   http://localhost:8000/docs"
echo ""
