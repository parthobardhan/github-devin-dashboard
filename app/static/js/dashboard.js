// GitHub-Devin Dashboard JavaScript

class Dashboard {
    constructor() {
        this.apiBase = '/api';
        this.init();
    }

    init() {
        this.setupEventListeners();
        // Removed auto-loading and auto-refresh to stop constant polling
        // Users must manually click refresh buttons to load data
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

    // Auto-refresh removed - now using manual refresh button to avoid constant API polling
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
