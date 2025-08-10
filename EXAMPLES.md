# GitHub-Devin Dashboard Examples

This document provides practical examples of using the GitHub-Devin Integration Dashboard.

## Basic Usage Examples

### 1. Setting Up Your First Repository

```bash
# 1. Configure your .env file
GITHUB_TOKEN=ghp_your_token_here
DEVIN_API_KEY=your_devin_key_here
GITHUB_REPOS=your-org/your-repo
APP_SECRET_KEY=your-secret-key-here

# 2. Start the dashboard
./scripts/run.sh

# 3. Access the dashboard
open http://localhost:8000
```

### 2. Analyzing Issues Programmatically

```python
import asyncio
import httpx

async def analyze_repository_issues():
    """Analyze all issues in a repository."""
    async with httpx.AsyncClient() as client:
        # Get all issues
        response = await client.get(
            "http://localhost:8000/api/github/repositories/owner/repo/issues"
        )
        issues = response.json()
        
        print(f"Found {len(issues['issues'])} issues")
        
        # Get dashboard analysis
        response = await client.get(
            "http://localhost:8000/api/dashboard/issues?repository=owner/repo"
        )
        analyzed_issues = response.json()
        
        # Print high-confidence issues
        for issue in analyzed_issues:
            if issue['analysis']['confidence_level'] == 'high':
                print(f"High confidence: #{issue['issue']['number']} - {issue['issue']['title']}")

# Run the analysis
asyncio.run(analyze_repository_issues())
```

### 3. Batch Processing Issues

```python
import asyncio
import httpx

async def batch_scope_issues():
    """Scope multiple issues at once."""
    async with httpx.AsyncClient() as client:
        # Get automation-ready issues
        response = await client.get(
            "http://localhost:8000/api/dashboard/issues/automation-ready?limit=5"
        )
        issues = response.json()
        
        # Scope each issue
        for issue in issues:
            repo = issue['issue']['repository']['full_name']
            number = issue['issue']['number']
            
            print(f"Scoping issue #{number} in {repo}")
            
            scope_response = await client.post(
                "http://localhost:8000/api/devin/scope-issue",
                json={
                    "repository_name": repo,
                    "issue_number": number
                }
            )
            
            if scope_response.status_code == 200:
                result = scope_response.json()
                print(f"  Session started: {result['session_id']}")
            else:
                print(f"  Failed: {scope_response.text}")

asyncio.run(batch_scope_issues())
```

## Advanced Workflows

### 1. Automated Issue Triage

```python
import asyncio
import httpx
from datetime import datetime, timedelta

class IssueTriageBot:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def triage_new_issues(self):
        """Automatically triage issues created in the last 24 hours."""
        async with httpx.AsyncClient() as client:
            # Get recent issues
            since = (datetime.now() - timedelta(days=1)).isoformat()
            
            response = await client.get(
                f"{self.base_url}/api/github/issues",
                params={"sort": "created", "direction": "desc"}
            )
            
            all_issues = response.json()
            
            # Filter for recent issues
            recent_issues = [
                issue for issue in all_issues 
                if datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')) > 
                   datetime.now() - timedelta(days=1)
            ]
            
            print(f"Found {len(recent_issues)} recent issues")
            
            # Analyze each issue
            for issue in recent_issues:
                await self.analyze_and_scope_issue(client, issue)
    
    async def analyze_and_scope_issue(self, client, issue):
        """Analyze an issue and scope it if suitable."""
        repo = issue['repository']['full_name'] if issue.get('repository') else 'unknown'
        number = issue['number']
        
        print(f"\nAnalyzing issue #{number}: {issue['title']}")
        
        # Get analysis
        response = await client.get(
            f"{self.base_url}/api/dashboard/issues",
            params={"repository": repo}
        )
        
        analyzed_issues = response.json()
        current_issue = next(
            (ai for ai in analyzed_issues if ai['issue']['number'] == number), 
            None
        )
        
        if not current_issue or not current_issue.get('analysis'):
            print("  No analysis available")
            return
        
        analysis = current_issue['analysis']
        confidence = analysis['overall_confidence']
        
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Complexity: {analysis['complexity_level']}")
        print(f"  Automation suitable: {analysis['automation_suitable']}")
        
        # Auto-scope high confidence issues
        if confidence >= 0.8 and analysis['automation_suitable']:
            print("  Auto-scoping high confidence issue...")
            
            scope_response = await client.post(
                f"{self.base_url}/api/devin/scope-issue",
                json={
                    "repository_name": repo,
                    "issue_number": number
                }
            )
            
            if scope_response.status_code == 200:
                result = scope_response.json()
                print(f"  ✅ Scoping session started: {result['session_id']}")
            else:
                print(f"  ❌ Scoping failed: {scope_response.text}")

# Usage
bot = IssueTriageBot()
asyncio.run(bot.triage_new_issues())
```

### 2. Monitoring Dashboard

```python
import asyncio
import httpx
import time
from datetime import datetime

class DashboardMonitor:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def monitor_sessions(self, interval=30):
        """Monitor active Devin sessions."""
        print("Starting session monitor...")
        
        while True:
            try:
                await self.check_session_status()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(interval)
    
    async def check_session_status(self):
        """Check status of all active sessions."""
        async with httpx.AsyncClient() as client:
            # Get dashboard stats
            response = await client.get(f"{self.base_url}/api/dashboard/stats")
            stats = response.json()
            
            # Get active sessions
            response = await client.get(f"{self.base_url}/api/devin/sessions")
            sessions = response.json()
            
            active_sessions = [s for s in sessions if s['status'] == 'running']
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Dashboard Status:")
            print(f"  Total Issues: {stats['total_issues']}")
            print(f"  Analyzed Issues: {stats['analyzed_issues']}")
            print(f"  Active Sessions: {len(active_sessions)}")
            print(f"  Success Rate: {stats['automation_success_rate']:.1%}")
            
            if active_sessions:
                print("  Active Sessions:")
                for session in active_sessions:
                    print(f"    - {session['session_id']}: {session.get('session_type', 'unknown')}")

# Usage
monitor = DashboardMonitor()
asyncio.run(monitor.monitor_sessions())
```

## Integration Examples

### 1. Slack Bot Integration

```python
import asyncio
import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class SlackIntegration:
    def __init__(self, slack_token, dashboard_url="http://localhost:8000"):
        self.slack = WebClient(token=slack_token)
        self.dashboard_url = dashboard_url
    
    async def notify_high_confidence_issues(self, channel="#dev-team"):
        """Notify Slack channel about high-confidence issues."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.dashboard_url}/api/dashboard/issues/automation-ready"
            )
            issues = response.json()
            
            if not issues:
                return
            
            message = "🤖 *High-Confidence Issues Ready for Automation*\n\n"
            
            for issue in issues[:5]:  # Limit to 5 issues
                repo = issue['issue']['repository']['full_name']
                number = issue['issue']['number']
                title = issue['issue']['title']
                confidence = issue['analysis']['overall_confidence']
                url = issue['issue']['html_url']
                
                message += f"• <{url}|#{number}> in `{repo}`: {title}\n"
                message += f"  Confidence: {confidence:.1%}\n\n"
            
            try:
                self.slack.chat_postMessage(
                    channel=channel,
                    text=message,
                    mrkdwn=True
                )
                print(f"Notified Slack about {len(issues)} issues")
            except SlackApiError as e:
                print(f"Slack notification failed: {e}")

# Usage
slack_bot = SlackIntegration("xoxb-your-slack-token")
asyncio.run(slack_bot.notify_high_confidence_issues())
```

### 2. GitHub Actions Integration

```yaml
# .github/workflows/devin-automation.yml
name: Devin Issue Automation

on:
  issues:
    types: [opened, labeled]
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM

jobs:
  analyze-issues:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install httpx
      
      - name: Analyze New Issues
        env:
          DASHBOARD_URL: ${{ secrets.DASHBOARD_URL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python scripts/github_actions_integration.py
```

```python
# scripts/github_actions_integration.py
import os
import asyncio
import httpx

async def main():
    dashboard_url = os.getenv('DASHBOARD_URL', 'http://localhost:8000')
    
    async with httpx.AsyncClient() as client:
        # Trigger analysis refresh
        response = await client.post(f"{dashboard_url}/api/dashboard/refresh")
        print(f"Dashboard refresh: {response.status_code}")
        
        # Get automation-ready issues
        response = await client.get(
            f"{dashboard_url}/api/dashboard/issues/automation-ready"
        )
        
        if response.status_code == 200:
            issues = response.json()
            print(f"Found {len(issues)} automation-ready issues")
            
            # Auto-scope the top 3 issues
            for issue in issues[:3]:
                repo = issue['issue']['repository']['full_name']
                number = issue['issue']['number']
                
                scope_response = await client.post(
                    f"{dashboard_url}/api/devin/scope-issue",
                    json={
                        "repository_name": repo,
                        "issue_number": number
                    }
                )
                
                if scope_response.status_code == 200:
                    result = scope_response.json()
                    print(f"Scoped issue #{number}: {result['session_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Custom Analysis Examples

### 1. Custom Confidence Scoring

```python
from app.services.analysis_service import AnalysisService
from app.models.github_models import GitHubIssue

class CustomAnalysisService(AnalysisService):
    def __init__(self):
        super().__init__()
        
        # Custom weights for your organization
        self.weights = {
            'requirements_clarity': 0.3,
            'technical_feasibility': 0.3,
            'scope_completeness': 0.2,
            'context_availability': 0.2
        }
        
        # Custom keywords for your domain
        self.complexity_keywords['low'].update({
            'typo', 'spelling', 'grammar', 'link', 'broken'
        })
        
        self.complexity_keywords['high'].update({
            'machine learning', 'ai', 'algorithm', 'optimization'
        })
    
    def _assess_requirements_clarity(self, issue: GitHubIssue) -> float:
        """Custom requirements clarity assessment."""
        score = super()._assess_requirements_clarity(issue)
        
        # Bonus for issues with acceptance criteria
        text = f"{issue.title} {issue.body or ''}".lower()
        if 'acceptance criteria' in text or 'definition of done' in text:
            score += 0.2
        
        # Bonus for issues with user stories
        if 'as a' in text and 'i want' in text and 'so that' in text:
            score += 0.15
        
        return min(1.0, score)

# Usage
custom_analyzer = CustomAnalysisService()
# Use in your application by replacing the default service
```

These examples demonstrate various ways to use and extend the GitHub-Devin Dashboard for your specific needs. Adapt them to your organization's workflow and requirements.
