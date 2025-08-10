# GitHub-Devin Integration Dashboard

A Python dashboard application that integrates GitHub Issues with Devin AI to automatically scope and complete development tasks.

## Features

- **GitHub Issues Integration**: Fetch and display issues from GitHub repositories
- **Devin AI Integration**: Trigger Devin sessions for issue scoping and completion
- **Confidence Scoring**: Analyze issues and assign confidence scores for automation
- **Real-time Dashboard**: Web-based interface for monitoring and managing workflows
- **Session Tracking**: Monitor Devin session progress and completion status

## Architecture

```
github-devin-dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── models/                # Pydantic models
│   │   ├── __init__.py
│   │   ├── github_models.py   # GitHub issue models
│   │   ├── devin_models.py    # Devin session models
│   │   └── dashboard_models.py # Dashboard data models
│   ├── services/              # Business logic services
│   │   ├── __init__.py
│   │   ├── github_service.py  # GitHub API integration
│   │   ├── devin_service.py   # Devin API integration
│   │   ├── analysis_service.py # Issue analysis and scoring
│   │   └── session_service.py # Session management
│   ├── api/                   # API endpoints
│   │   ├── __init__.py
│   │   ├── github_routes.py   # GitHub-related endpoints
│   │   ├── devin_routes.py    # Devin-related endpoints
│   │   └── dashboard_routes.py # Dashboard endpoints
│   └── static/                # Static files (CSS, JS)
│       ├── css/
│       ├── js/
│       └── templates/         # HTML templates
├── tests/                     # Test files
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Quick Start

### Automated Setup (Recommended)

1. **Run the setup script**:
   ```bash
   cd github-devin-dashboard
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Configure your API keys**:
   ```bash
   # Edit the .env file with your credentials
   nano .env
   ```

3. **Start the dashboard**:
   ```bash
   chmod +x scripts/run.sh
   ./scripts/run.sh
   ```

### Manual Setup

1. **Clone and Setup Environment**:
   ```bash
   cd github-devin-dashboard
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Run the Application**:
   ```bash
   # Option 1: Using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Option 2: Using Python module
   python -m app.main
   ```

4. **Access Dashboard**:
   - Dashboard: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Configuration

### Required API Keys

1. **GitHub Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with `repo` and `issues` permissions
   - Add to `.env` as `GITHUB_TOKEN=your_token_here`

2. **Devin API Key**:
   - Get your API key from [Devin Settings](https://app.devin.ai/settings/api-keys)
   - Add to `.env` as `DEVIN_API_KEY=your_key_here`

3. **Repository Configuration**:
   - List repositories to monitor in `GITHUB_REPOS=owner/repo1,owner/repo2`
   - Ensure your GitHub token has access to these repositories

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | Yes | - |
| `DEVIN_API_KEY` | Devin API key | Yes | - |
| `GITHUB_REPOS` | Comma-separated list of repositories | Yes | - |
| `APP_SECRET_KEY` | Secret key for sessions | Yes | - |
| `APP_HOST` | Host to bind the server | No | `0.0.0.0` |
| `APP_PORT` | Port to bind the server | No | `8000` |
| `APP_DEBUG` | Enable debug mode | No | `false` |
| `CONFIDENCE_THRESHOLD` | Minimum confidence for automation | No | `0.7` |
| `ANALYSIS_TIMEOUT` | Timeout for issue analysis (seconds) | No | `300` |

## Usage Guide

### Dashboard Overview

The dashboard provides a comprehensive view of your GitHub issues and Devin automation status:

1. **Issue Analysis**: Automatically analyzes GitHub issues for automation suitability
2. **Confidence Scoring**: Assigns confidence scores based on requirement clarity and complexity
3. **Devin Integration**: Triggers Devin sessions for issue scoping and completion
4. **Progress Monitoring**: Real-time tracking of session status and results

### Workflow

#### 1. Issue Discovery
- Dashboard automatically fetches issues from configured repositories
- Issues are analyzed and assigned confidence scores
- High-confidence issues are flagged for automation

#### 2. Issue Scoping
```bash
# Via API
curl -X POST "http://localhost:8000/api/devin/scope-issue" \
  -H "Content-Type: application/json" \
  -d '{"repository_name": "owner/repo", "issue_number": 123}'

# Via Dashboard
# Click "Scope Issue" button on any issue card
```

#### 3. Issue Completion
```bash
# Via API
curl -X POST "http://localhost:8000/api/devin/complete-issue" \
  -H "Content-Type: application/json" \
  -d '{"repository_name": "owner/repo", "issue_number": 123}'

# Via Dashboard
# Click "Complete Issue" button on scoped issues
```

#### 4. Monitor Progress
- View active sessions in the dashboard
- Check session status via API
- Receive notifications when sessions complete

### Best Practices

1. **Start with High-Confidence Issues**: Begin with issues that have confidence scores > 0.8
2. **Review Scoping Results**: Always review Devin's scoping analysis before proceeding
3. **Monitor Sessions**: Keep track of active sessions to avoid overloading
4. **Iterative Improvement**: Use feedback to improve issue descriptions and labels

## API Reference

### GitHub Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/github/repositories` | List configured repositories |
| `GET` | `/api/github/issues` | Get all issues across repositories |
| `GET` | `/api/github/repositories/{repo}/issues` | Get issues from specific repository |
| `GET` | `/api/github/repositories/{repo}/issues/{number}` | Get specific issue |
| `GET` | `/api/github/repositories/{repo}/issues/{number}/comments` | Get issue comments |
| `GET` | `/api/github/stats` | Get GitHub statistics |

### Devin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/devin/sessions` | List all Devin sessions |
| `POST` | `/api/devin/sessions` | Create new Devin session |
| `GET` | `/api/devin/sessions/{id}` | Get session details |
| `POST` | `/api/devin/sessions/{id}/messages` | Send message to session |
| `POST` | `/api/devin/scope-issue` | Trigger issue scoping |
| `POST` | `/api/devin/complete-issue` | Trigger issue completion |
| `POST` | `/api/devin/batch-scope` | Batch scope multiple issues |
| `GET` | `/api/devin/stats` | Get Devin statistics |

### Dashboard Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard/stats` | Get dashboard statistics |
| `GET` | `/api/dashboard/issues` | Get issues with analysis |
| `GET` | `/api/dashboard/issues/automation-ready` | Get automation-ready issues |
| `GET` | `/api/dashboard/repositories/{repo}/stats` | Get repository statistics |
| `GET` | `/api/dashboard/summary` | Get dashboard summary |
| `POST` | `/api/dashboard/refresh` | Refresh dashboard data |

### Example API Calls

#### Get Dashboard Statistics
```bash
curl -X GET "http://localhost:8000/api/dashboard/stats"
```

#### Scope an Issue
```bash
curl -X POST "http://localhost:8000/api/devin/scope-issue" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_name": "owner/repo",
    "issue_number": 123
  }'
```

#### Get Automation-Ready Issues
```bash
curl -X GET "http://localhost:8000/api/dashboard/issues/automation-ready?min_confidence=0.8&limit=10"
```

#### Check Session Status
```bash
curl -X GET "http://localhost:8000/api/devin/sessions/devin-xxx"
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_github_service.py
```

### Code Quality

```bash
# Format code
black app/ tests/

# Check code style
flake8 app/ tests/

# Type checking
mypy app/

# Run all quality checks
black app/ && flake8 app/ && mypy app/
```

### Project Structure

```
github-devin-dashboard/
├── app/                    # Main application code
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── config.py          # Configuration management
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   ├── api/               # API route handlers
│   └── static/            # Static assets
├── scripts/               # Setup and utility scripts
├── tests/                 # Test files
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup
├── .env.example          # Environment template
└── README.md             # This file
```

## Troubleshooting

### Common Issues

#### 1. GitHub API Rate Limiting
```
Error: API rate limit exceeded
```
**Solution**:
- Ensure you're using a personal access token (not anonymous)
- Consider upgrading to GitHub Pro for higher rate limits
- Implement request caching in production

#### 2. Devin API Authentication
```
Error: Unauthorized: Invalid Devin API key
```
**Solution**:
- Verify your API key in the Devin dashboard
- Ensure the key has necessary permissions
- Check that the key is correctly set in `.env`

#### 3. Repository Access Issues
```
Error: Repository not found
```
**Solution**:
- Verify repository names are in `owner/repo` format
- Ensure your GitHub token has access to the repositories
- Check that repositories exist and are not private (unless token has access)

#### 4. Session Timeout Issues
```
Error: Session timeout during analysis
```
**Solution**:
- Increase `ANALYSIS_TIMEOUT` in `.env`
- Check Devin service status
- Retry with simpler issues first

### Performance Optimization

1. **Caching**: Implement Redis for session and analysis caching
2. **Database**: Use PostgreSQL for production instead of SQLite
3. **Background Tasks**: Use Celery for long-running operations
4. **Rate Limiting**: Implement API rate limiting for production use

### Monitoring and Logging

- Logs are written to stdout in JSON format
- Use `LOG_LEVEL=DEBUG` for detailed debugging
- Monitor API response times and error rates
- Set up alerts for failed Devin sessions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write tests for new features
- Update documentation for API changes
- Use structured logging with context

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/example/github-devin-dashboard/issues)
- 📖 Documentation: [API Docs](http://localhost:8000/docs)
- 💬 Discussions: [GitHub Discussions](https://github.com/example/github-devin-dashboard/discussions)
