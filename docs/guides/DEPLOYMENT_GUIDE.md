# 🚀 Deployment Guide - NLU-Enhanced Chatbot

## Overview

This guide provides step-by-step instructions for deploying the BenchmarkOS Chatbot with its enhanced Natural Language Understanding capabilities.

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Deployment](#deployment)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedure](#rollback-procedure)

---

## System Requirements

### Hardware Requirements

**Minimum**:
- CPU: 2 cores, 2.0 GHz
- RAM: 4 GB
- Storage: 10 GB available space
- Network: 100 Mbps

**Recommended**:
- CPU: 4+ cores, 2.5+ GHz
- RAM: 8+ GB
- Storage: 20+ GB SSD
- Network: 1 Gbps

### Software Requirements

- **Python**: 3.8 or higher (3.10+ recommended)
- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Package Manager**: pip 21.0+
- **Optional**: Docker 20.10+ (for containerized deployment)

### External Dependencies

- **OpenAI API**: Access key required for LLM functionality
- **Database**: PostgreSQL 12+ or compatible
- **Web Server**: Uvicorn (included) or Gunicorn

---

## Pre-Deployment Checklist

### ✅ Code Validation

- [ ] All 790 NLU tests pass
- [ ] No linter errors or warnings
- [ ] Performance benchmarks meet targets (<100ms typical)
- [ ] Code review completed
- [ ] Documentation is up to date

### ✅ Configuration

- [ ] Environment variables configured
- [ ] API keys obtained and secured
- [ ] Database connection tested
- [ ] Logging configured
- [ ] Error tracking configured (optional)

### ✅ Infrastructure

- [ ] Server provisioned
- [ ] SSL certificates obtained (if HTTPS)
- [ ] Domain name configured (if applicable)
- [ ] Firewall rules configured
- [ ] Backup system in place

### ✅ Security

- [ ] API keys stored securely (not in code)
- [ ] Input validation enabled
- [ ] Rate limiting configured
- [ ] CORS policies set
- [ ] Security headers configured

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/Team2-CBA-Project.git
cd Team2-CBA-Project
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 4: Verify Installation

```bash
# Run quick test
python -c "from finanlyzeos_chatbot.chatbot import BenchmarkOSChatbot; print('✅ Import successful')"

# Run full test suite (optional but recommended)
pytest tests/ -v
```

Expected output:
```
======================== 790 passed in X seconds ========================
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/finanlyzeos

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/finanlyzeos/chatbot.log

# Feature Flags
ENABLE_SPELLING_CORRECTION=true
ENABLE_ADVANCED_NLU=true
ENABLE_CACHING=false  # Disable for production (prevent hallucinations)

# Performance
PARSING_TIMEOUT_MS=500
MAX_QUERY_LENGTH=1000
```

### Application Configuration

Edit `config.py` (if applicable):

```python
# config.py
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# NLU Configuration
NLU_CONFIG = {
    "spelling_correction": {
        "enabled": True,
        "min_confidence": 0.75,
    },
    "comparative_language": {
        "enabled": True,
    },
    "trend_detection": {
        "enabled": True,
    },
    # ... etc for all 14 features
}

# Performance
PERFORMANCE_CONFIG = {
    "parsing_timeout": 0.5,  # seconds
    "max_ticker_candidates": 50,
    "fuzzy_match_threshold": 0.80,
}

# Logging
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.getenv("LOG_FILE", "chatbot.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "default",
        },
    },
    "root": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "handlers": ["console", "file"],
    },
}
```

---

## Testing

### Pre-Deployment Testing

#### 1. Unit Tests

```bash
# Run all unit tests
pytest tests/ -v

# Run specific feature tests
pytest tests/test_comparative_language.py -v
pytest tests/test_spelling_correction.py -v
```

#### 2. Integration Tests

```bash
# Run integration tests
pytest tests/test_integration_e2e.py -v
```

#### 3. Performance Tests

```bash
# Run performance benchmarks
pytest tests/test_performance_benchmarks.py -v

# Expected output:
# ✅ Simple queries: ~12ms
# ✅ Typical queries: 26-68ms
# ✅ Complex queries: 68-117ms
```

#### 4. Manual Testing

Start the server locally:

```bash
# Terminal 1: Start backend
python3 serve_chatbot.py --host 127.0.0.1 --port 8000

# Terminal 2: Test queries
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Apple revenue last year?"}'
```

Test key scenarios:
- ✅ Basic questions
- ✅ Spelling errors
- ✅ Comparisons
- ✅ Follow-up questions
- ✅ Company groups (FAANG, etc.)
- ✅ Abbreviations (YoY, P/E, etc.)
- ✅ Complex multi-feature queries

---

## Deployment

### Option 1: Direct Deployment (Simple)

**Best for**: Development, testing, small-scale production

```bash
# Activate virtual environment
source venv/bin/activate

# Start server
python3 serve_chatbot.py \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4

# Or with environment variables
HOST=0.0.0.0 PORT=8000 WORKERS=4 python3 serve_chatbot.py
```

**Process Management** (keep alive):

```bash
# Using screen
screen -S chatbot
python3 serve_chatbot.py --host 0.0.0.0 --port 8000
# Press Ctrl+A, then D to detach

# Using nohup
nohup python3 serve_chatbot.py --host 0.0.0.0 --port 8000 > chatbot.log 2>&1 &

# Using systemd (recommended)
sudo systemctl start finanlyzeos-chatbot
sudo systemctl enable finanlyzeos-chatbot  # Auto-start on boot
```

**systemd Service File** (`/etc/systemd/system/finanlyzeos-chatbot.service`):

```ini
[Unit]
Description=BenchmarkOS Chatbot Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Team2-CBA-Project
Environment="PATH=/path/to/Team2-CBA-Project/venv/bin"
ExecStart=/path/to/Team2-CBA-Project/venv/bin/python3 serve_chatbot.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Option 2: Docker Deployment (Recommended)

**Best for**: Production, scalability, consistency

**Dockerfile**:

```dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run application
CMD ["python3", "serve_chatbot.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  chatbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - LOG_LEVEL=INFO
      - ENABLE_CACHING=false
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - chatbot
    restart: unless-stopped
```

**Build and Deploy**:

```bash
# Build image
docker build -t finanlyzeos-chatbot:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  --name finanlyzeos-chatbot \
  finanlyzeos-chatbot:latest

# Or use docker-compose
docker-compose up -d

# Check logs
docker logs -f finanlyzeos-chatbot

# Stop
docker-compose down
```

### Option 3: Cloud Deployment

#### AWS (EC2 + ECS)

```bash
# 1. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag finanlyzeos-chatbot:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/finanlyzeos-chatbot:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/finanlyzeos-chatbot:latest

# 2. Deploy to ECS
aws ecs update-service --cluster chatbot-cluster --service chatbot-service --force-new-deployment
```

#### Google Cloud (Cloud Run)

```bash
# 1. Build and push
gcloud builds submit --tag gcr.io/your-project/finanlyzeos-chatbot

# 2. Deploy
gcloud run deploy finanlyzeos-chatbot \
  --image gcr.io/your-project/finanlyzeos-chatbot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

#### Azure (Container Instances)

```bash
# 1. Push to ACR
az acr build --registry myregistry --image finanlyzeos-chatbot:latest .

# 2. Deploy
az container create \
  --resource-group myResourceGroup \
  --name finanlyzeos-chatbot \
  --image myregistry.azurecr.io/finanlyzeos-chatbot:latest \
  --dns-name-label finanlyzeos-chatbot \
  --ports 8000
```

---

## Monitoring

### Health Check Endpoint

```bash
# Check if service is running
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-11-04T12:00:00Z",
  "version": "1.0.0"
}
```

### Performance Monitoring

**Key Metrics to Track**:

1. **Response Time**:
   - P50 (median): <100ms
   - P95: <200ms
   - P99: <500ms

2. **Parsing Time**:
   - Average: <50ms
   - P95: <100ms
   - P99: <200ms

3. **Error Rate**:
   - Target: <1%
   - Alert threshold: >5%

4. **API Rate Limiting**:
   - OpenAI API calls per minute
   - Cost per query

**Logging**:

```python
# Log all queries and responses
import logging
logger = logging.getLogger(__name__)

logger.info(f"Query received: {query}")
logger.info(f"Parsing time: {parse_time_ms}ms")
logger.info(f"Response generated: {len(response)} chars")
logger.error(f"Error occurred: {error}", exc_info=True)
```

**Metrics Collection** (optional):

```python
# Using Prometheus
from prometheus_client import Counter, Histogram, start_http_server

query_counter = Counter('chatbot_queries_total', 'Total queries')
parse_time = Histogram('chatbot_parse_time_seconds', 'Parse time')
error_counter = Counter('chatbot_errors_total', 'Total errors')

# In your code:
query_counter.inc()
with parse_time.time():
    result = parse_query(query)
```

---

## Troubleshooting

### Issue: Server Won't Start

**Symptoms**: Error when running `serve_chatbot.py`

**Solutions**:
```bash
# Check if port is already in use
sudo lsof -i :8000
sudo netstat -tuln | grep 8000

# Kill existing process
pkill -9 -f "serve_chatbot"

# Try different port
python3 serve_chatbot.py --port 8001
```

### Issue: Import Errors

**Symptoms**: `ModuleNotFoundError` or `ImportError`

**Solutions**:
```bash
# Verify virtual environment is activated
which python3  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version
python3 --version  # Should be 3.8+
```

### Issue: Slow Responses

**Symptoms**: Queries taking >1 second

**Solutions**:
```bash
# Run performance tests
pytest tests/test_performance_benchmarks.py -v

# Profile parsing
python -m cProfile -s cumtime -m pytest tests/test_performance_benchmarks.py

# Check database connection
# Check OpenAI API latency
# Verify no caching issues
```

### Issue: Incorrect Responses

**Symptoms**: Wrong data or "hallucinations"

**Solutions**:
1. **Disable Caching**:
   ```python
   # In web.py
   cacheable = False
   ```

2. **Clear All Caches**:
   ```python
   _summary_cache.clear()
   _dashboard_cache.clear()
   ```

3. **Check Data Freshness**:
   - When was data last updated?
   - Is database connection working?

### Issue: High Memory Usage

**Symptoms**: Memory growing over time

**Solutions**:
```bash
# Monitor memory
ps aux | grep serve_chatbot

# Check for memory leaks
import tracemalloc
tracemalloc.start()
# ... run queries ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

---

## Rollback Procedure

### If Deployment Fails

**Step 1: Stop New Version**
```bash
# systemd
sudo systemctl stop finanlyzeos-chatbot

# Docker
docker-compose down

# Process
pkill -9 -f "serve_chatbot"
```

**Step 2: Restore Previous Version**
```bash
# Git
git checkout <previous-commit-hash>
git checkout tags/v0.9.0  # Or previous tag

# Docker
docker run -d -p 8000:8000 finanlyzeos-chatbot:v0.9.0
```

**Step 3: Verify Rollback**
```bash
# Test critical functionality
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Apple revenue?"}'

# Check logs
tail -f /var/log/finanlyzeos/chatbot.log
```

**Step 4: Notify Stakeholders**
- Document what went wrong
- Estimated time to fix
- Next steps

---

## Post-Deployment

### ✅ Verification Checklist

After deployment, verify:

- [ ] Server is accessible
- [ ] Health check endpoint responds
- [ ] Basic queries work
- [ ] Advanced NLU features work
- [ ] Follow-up questions work
- [ ] Performance meets targets
- [ ] Logs are being written
- [ ] Monitoring is active
- [ ] Backups are running

### 📊 Performance Baseline

Record initial metrics:
- Average response time: ______ms
- P95 response time: ______ms
- Average parsing time: ______ms
- Memory usage: ______MB
- CPU usage: ______%

### 📝 Documentation

Update:
- [ ] Deployment date and version
- [ ] Configuration changes
- [ ] Known issues
- [ ] Contact information
- [ ] Runbook for common issues

---

## Support

### Getting Help

1. **Check Logs**: `/var/log/finanlyzeos/chatbot.log`
2. **Review Documentation**: `docs/`
3. **Run Tests**: `pytest tests/ -v`
4. **Contact Team**: your-team@example.com

### Useful Commands

```bash
# Check service status
sudo systemctl status finanlyzeos-chatbot

# View logs
tail -f /var/log/finanlyzeos/chatbot.log
docker logs -f finanlyzeos-chatbot

# Restart service
sudo systemctl restart finanlyzeos-chatbot
docker-compose restart

# Check resource usage
htop
docker stats

# Test query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

---

## Known Limitations

1. **Real-time Data**: Not connected to live market feeds
2. **Data Availability**: Limited to data in database
3. **Query Length**: Max 1000 characters (configurable)
4. **Rate Limiting**: Subject to OpenAI API limits
5. **Language**: English only

---

## Future Enhancements

Potential improvements for next version:
- [ ] Multi-language support
- [ ] Real-time market data integration
- [ ] Voice input/output
- [ ] Mobile app
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework

---

**Version**: 1.0  
**Last Updated**: November 2025  
**Maintained By**: BenchmarkOS Team  
**Next Review**: Quarterly

