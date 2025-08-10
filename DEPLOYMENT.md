# Deployment Guide

This guide covers deploying the GitHub-Devin Integration Dashboard to production environments.

## Production Deployment Options

### 1. Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose

```yaml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - DEVIN_API_KEY=${DEVIN_API_KEY}
      - GITHUB_REPOS=${GITHUB_REPOS}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - DATABASE_URL=postgresql://user:password@postgres:5432/dashboard
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=dashboard
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - dashboard
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Build and Deploy

```bash
# Build the image
docker build -t github-devin-dashboard .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f dashboard

# Scale the application
docker-compose up -d --scale dashboard=3
```

### 2. Kubernetes Deployment

#### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: github-devin-dashboard

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dashboard-config
  namespace: github-devin-dashboard
data:
  APP_HOST: "0.0.0.0"
  APP_PORT: "8000"
  APP_DEBUG: "false"
  LOG_LEVEL: "INFO"
  CONFIDENCE_THRESHOLD: "0.7"
  ANALYSIS_TIMEOUT: "300"
```

#### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: dashboard-secrets
  namespace: github-devin-dashboard
type: Opaque
data:
  GITHUB_TOKEN: <base64-encoded-token>
  DEVIN_API_KEY: <base64-encoded-key>
  APP_SECRET_KEY: <base64-encoded-secret>
  DATABASE_URL: <base64-encoded-url>
```

#### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dashboard
  namespace: github-devin-dashboard
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dashboard
  template:
    metadata:
      labels:
        app: dashboard
    spec:
      containers:
      - name: dashboard
        image: github-devin-dashboard:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dashboard-config
        - secretRef:
            name: dashboard-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dashboard-service
  namespace: github-devin-dashboard
spec:
  selector:
    app: dashboard
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dashboard-ingress
  namespace: github-devin-dashboard
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - dashboard.yourdomain.com
    secretName: dashboard-tls
  rules:
  - host: dashboard.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard-service
            port:
              number: 80
```

#### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n github-devin-dashboard

# Check logs
kubectl logs -f deployment/dashboard -n github-devin-dashboard

# Scale deployment
kubectl scale deployment dashboard --replicas=5 -n github-devin-dashboard
```

### 3. Cloud Platform Deployments

#### AWS ECS with Fargate

```json
{
  "family": "github-devin-dashboard",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "dashboard",
      "image": "your-account.dkr.ecr.region.amazonaws.com/github-devin-dashboard:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "APP_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "APP_PORT",
          "value": "8000"
        }
      ],
      "secrets": [
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:github-token"
        },
        {
          "name": "DEVIN_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:devin-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/github-devin-dashboard",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

#### Google Cloud Run

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: github-devin-dashboard
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      containerConcurrency: 100
      containers:
      - image: gcr.io/your-project/github-devin-dashboard:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_HOST
          value: "0.0.0.0"
        - name: APP_PORT
          value: "8000"
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token
              key: token
        - name: DEVIN_API_KEY
          valueFrom:
            secretKeyRef:
              name: devin-api-key
              key: key
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

```bash
# Deploy to Cloud Run
gcloud run services replace cloudrun.yaml --region=us-central1
```

## Production Configuration

### Environment Variables

```bash
# Production .env
APP_DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database
DATABASE_URL=postgresql://user:password@db-host:5432/dashboard

# Redis for caching
REDIS_URL=redis://redis-host:6379/0

# Security
APP_SECRET_KEY=your-very-secure-secret-key-here

# API Configuration
GITHUB_TOKEN=ghp_your_production_token
DEVIN_API_KEY=your_production_devin_key
GITHUB_REPOS=org/repo1,org/repo2,org/repo3

# Performance
MAX_CONCURRENT_SESSIONS=10
ANALYSIS_TIMEOUT=600
CONFIDENCE_THRESHOLD=0.8

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
DATADOG_API_KEY=your-datadog-key
```

### Nginx Configuration

```nginx
# nginx.conf
upstream dashboard {
    server dashboard:8000;
}

server {
    listen 80;
    server_name dashboard.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {
        proxy_pass http://dashboard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files caching
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        access_log off;
        proxy_pass http://dashboard;
    }
}
```

## Monitoring and Observability

### Prometheus Metrics

```python
# Add to app/main.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
DEVIN_SESSIONS = Counter('devin_sessions_total', 'Total Devin sessions', ['type', 'status'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Logging Configuration

```python
# app/logging_config.py
import structlog
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(colors=False),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/dashboard.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## Security Considerations

### 1. API Key Management

- Use environment variables or secret management systems
- Rotate API keys regularly
- Implement key rotation without downtime
- Monitor API key usage

### 2. Network Security

- Use HTTPS in production
- Implement proper CORS policies
- Use VPC/private networks where possible
- Implement rate limiting

### 3. Authentication & Authorization

```python
# Add to app/main.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Protect sensitive endpoints
@app.post("/api/devin/scope-issue", dependencies=[Depends(verify_token)])
async def scope_issue_protected(...):
    # Implementation
    pass
```

## Backup and Recovery

### Database Backups

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="dashboard"

# Create backup
pg_dump $DATABASE_URL > "$BACKUP_DIR/dashboard_$DATE.sql"

# Compress backup
gzip "$BACKUP_DIR/dashboard_$DATE.sql"

# Clean old backups (keep last 30 days)
find $BACKUP_DIR -name "dashboard_*.sql.gz" -mtime +30 -delete

echo "Backup completed: dashboard_$DATE.sql.gz"
```

### Application State Backup

```python
# backup_state.py
import json
import asyncio
from app.services.session_service import SessionService

async def backup_application_state():
    """Backup application state to JSON."""
    service = SessionService()
    
    # Get all data
    stats = await service.get_dashboard_stats()
    issues = await service.get_dashboard_issues(limit=1000)
    
    backup_data = {
        "timestamp": datetime.now().isoformat(),
        "stats": stats.dict(),
        "issues": [issue.dict() for issue in issues],
    }
    
    # Save to file
    with open(f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(backup_data, f, indent=2, default=str)

if __name__ == "__main__":
    asyncio.run(backup_application_state())
```

This deployment guide provides comprehensive instructions for deploying the GitHub-Devin Dashboard in various production environments with proper security, monitoring, and backup strategies.
