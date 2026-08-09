# AI Job Seeker

An AI-powered job search and evaluation platform built with Django. Fetch job listings in bulk, evaluate them against your preferences using multiple AI providers, and manage everything from a web dashboard.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Linux/macOS Setup](#linuxmacos-setup)
  - [Windows Setup](#windows-setup)
  - [Docker Setup](#docker-setup-all-platforms)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [AI Provider Setup](#ai-provider-setup)
  - [Database Configuration](#database-configuration)
- [Services Setup](#services-setup)
- [Usage Guide](#usage-guide)
- [AI Providers](#ai-providers)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [Quick Start Commands](#quick-start-commands)

## Prerequisites

### Linux

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib redis-server
sudo apt install -y build-essential libpq-dev libssl-dev libffi-dev
```

### macOS

```bash
# Install using Homebrew
brew install python3 postgresql redis
brew services start postgresql
brew services start redis
```

### Windows

Download and install:
1. [Python 3.10+](https://www.python.org/downloads/windows/)
2. [PostgreSQL](https://www.postgresql.org/download/windows/)
3. [Redis](https://github.com/microsoftarchive/redis/releases)

## Installation

### Linux/macOS Setup

#### Option 1: Complete Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/job_seeker.git
cd job_seeker

# Make scripts executable
chmod +x scripts/*.sh

# Run the complete setup script
./scripts/linux_setup.sh
```

#### Option 2: Manual Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
./scripts/linux_psql.sh

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Windows Setup

#### Option 1: PowerShell Automated Setup (Recommended)

```powershell
# Open PowerShell as Administrator
cd C:\path\to\job_seeker

# Run the complete setup script
.\scripts\powershell_setup.ps1
```

#### Option 2: Manual Setup

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Setup database
.\scripts\windows_powershell_psql.ps1

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Docker Setup (All Platforms)

```bash
# Build and run containers
docker-compose up -d --build

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Access the application
# http://localhost:8000
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with these settings:

```env
# ============================================
# DJANGO CORE SETTINGS
# ============================================
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# ============================================
# DATABASE SETTINGS
# ============================================
DATABASE_URL=postgresql://jobuser:jobpass@localhost:5432/job_seeker
DB_USER=jobuser
DB_PASS=jobpass
DB_NAME=job_seeker
DB_HOST=localhost
DB_PORT=5432

# ============================================
# REDIS & CELERY SETTINGS
# ============================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ============================================
# AI PROVIDER API KEYS
# ============================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
GROQ_API_KEY=gsk_...

# ============================================
# AI PROVIDER SELECTION
# ============================================
AI_PROVIDER_PREFERENCE=groq
AI_MODEL=llama-3.3-70b-versatile
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000

# ============================================
# JOB FETCHING SETTINGS
# ============================================
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
REQUEST_TIMEOUT=120
MAX_RETRIES=10
CACHE_TTL=3600

# ============================================
# FEATURE FLAGS
# ============================================
AI_DUPLICATE_DETECTION=True
AI_JOB_ENRICHMENT=True
AUTO_EVALUATE_JOBS=True
USE_LOCAL_AI=False
```

### AI Provider Setup

#### Groq (Recommended — Fast & Free)

1. Sign up at [console.groq.com](https://console.groq.com)
2. Get an API key: **API Keys → Create API Key**
3. Add to `.env`: `GROQ_API_KEY=gsk_your_key_here`
4. Set preference: `AI_PROVIDER_PREFERENCE=groq`

#### OpenAI

1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Get an API key: **API Keys → Create new secret key**
3. Add to `.env`: `OPENAI_API_KEY=sk-...`
4. Set preference: `AI_PROVIDER_PREFERENCE=openai`

#### Anthropic Claude

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Get an API key: **Account → API Keys**
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. Set preference: `AI_PROVIDER_PREFERENCE=anthropic`

#### Google Gemini

1. Sign up at [makersuite.google.com](https://makersuite.google.com)
2. Get an API key: **Create API Key**
3. Add to `.env`: `GOOGLE_API_KEY=AIza...`
4. Set preference: `AI_PROVIDER_PREFERENCE=gemini`

### Database Configuration

#### PostgreSQL Setup (Linux/macOS)

```bash
./scripts/linux_psql.sh
```

#### PostgreSQL Setup (Windows)

```powershell
.\scripts\windows_powershell_psql.ps1
```

#### Manual Database Setup

```sql
-- Connect to PostgreSQL
sudo -u postgres psql

-- Create user
CREATE USER jobuser WITH PASSWORD 'jobpass';

-- Create database
CREATE DATABASE job_seeker OWNER jobuser;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE job_seeker TO jobuser;
\c job_seeker
GRANT ALL ON SCHEMA public TO jobuser;
```

## Services Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Start Redis
sudo systemctl start redis       # Linux
brew services start redis        # macOS

# Start Celery (in a new terminal)
celery -A job_seeker worker -l info

# Start Django (in another terminal)
python manage.py runserver
```

## Usage Guide

### Adding Job Sources

**Single source (web interface)**

1. Navigate to `http://localhost:8000/add-jobs/`
2. Fill in the form:
   - **URL**: e.g. `https://www.linkedin.com/jobs/search/?keywords=python`
   - **Source Type**: select from the dropdown
   - **Name**: a descriptive name
3. Click **Fetch Jobs with AI**

**Single source (admin panel)**

1. Go to `http://localhost:8000/admin/jobs/jobsource/add/`
2. Fill in the form and save — the system processes the source automatically

### Bulk Job Processing

**Web interface (recommended)**

1. Navigate to `http://localhost:8000/bulk-add-jobs/`
2. Paste URLs, one per line:
   ```
   https://www.linkedin.com/jobs/search/?keywords=python
   https://www.indeed.com/jobs?q=python
   https://www.glassdoor.com/Job/index.htm
   ```
3. Select a **Source Type** (default: "Other")
4. Click **Process All URLs with AI**
5. Monitor progress in real time

**Management command**

```bash
# Process all active sources
python manage.py process_jobs --all

# Process a specific source
python manage.py process_jobs --source-id 1

# Process with AI evaluation
python manage.py process_jobs --all --user-id 1

# Process without AI (faster)
python manage.py process_jobs --all --no-ai
```

**Python script**

```bash
# Create a file with URLs
echo "https://www.linkedin.com/jobs/search/?keywords=python" > urls.txt
echo "https://www.indeed.com/jobs?q=python" >> urls.txt

# Process them
python scripts/bulk_process.py urls.txt
```

### Viewing Jobs

- **All jobs**: `http://localhost:8000/jobs/`
- **Job details**: click any job title
- **Filter**: use the sidebar filters
- **Sort**: by date, relevance, or salary

**API endpoints**

```bash
# Get all jobs
curl http://localhost:8000/api/jobs/

# Get job details
curl http://localhost:8000/api/jobs/1/

# Search jobs
curl http://localhost:8000/api/jobs/?search=python

# Filter by location
curl http://localhost:8000/api/jobs/?location=Remote
```

### AI Evaluation

**Automated evaluation**
New jobs are automatically evaluated when added. Evaluation includes match score, skill match, and culture fit, and results are stored in the database.

**Manual evaluation**

1. Go to the job list: `http://localhost:8000/jobs/`
2. Click **Analyze** on any job
3. Wait for the AI analysis to complete
4. View results on the job detail page

**Bulk evaluation**

1. Go to the job list: `http://localhost:8000/jobs/`
2. Click **Evaluate with AI** at the top
3. All jobs are evaluated in bulk, with real-time progress updates

### User Preferences

**Setting preferences**

1. Navigate to `http://localhost:8000/preferences/`
2. Configure:
   - Location preferences
   - Remote/hybrid work preferences
   - Job types and experience levels
   - Salary range
   - Include/exclude keywords
3. Click **Save Preferences**

**AI recommendations**
Preferences automatically trigger AI re-evaluation, so jobs are re-scored and recommendations are personalized to you.

### Admin Dashboard

**Access**: `http://localhost:8000/admin/` — log in with your superuser credentials.

**Manage:**
- Users and permissions
- Job sources
- Jobs and evaluations
- User preferences

**Features:**
- **Job management** — view, edit, delete jobs
- **Source management** — add, activate/deactivate sources
- **User management** — manage users and permissions
- **Preferences** — view/edit user preferences
- **System monitoring** — check processing status

## AI Providers

### Provider Comparison

| Provider  | Model         | Speed | Cost  | Quality | Best For                    |
|-----------|---------------|:-----:|:-----:|:-------:|------------------------------|
| Groq      | Llama 3.3 70B | ⚡⚡⚡⚡⚡ | Free/$$ | ⭐⭐⭐⭐  | Production, speed           |
| OpenAI    | GPT-4         | ⚡⚡⚡  | $$$   | ⭐⭐⭐⭐⭐ | Maximum quality             |
| Anthropic | Claude 3      | ⚡⚡⚡  | $$$   | ⭐⭐⭐⭐⭐ | Complex analysis            |
| Gemini    | Gemini Pro    | ⚡⚡⚡  | $$    | ⭐⭐⭐⭐  | Google ecosystem            |
| Local     | Various       | ⚡⚡   | Free  | ⭐⭐⭐   | Offline, privacy            |

### Choosing a Provider

**Groq (Recommended)**
- **Pros**: fastest, free tier available, excellent quality
- **Cons**: limited model selection
- **Best for**: production use, high-volume processing

**OpenAI**
- **Pros**: best quality, wide model selection
- **Cons**: expensive, rate limited
- **Best for**: high-quality analysis, complex tasks

**Anthropic**
- **Pros**: excellent reasoning, large context
- **Cons**: expensive, limited availability
- **Best for**: detailed job analysis

**Google Gemini**
- **Pros**: good quality, integrates with Google
- **Cons**: limited free tier, slower
- **Best for**: research, testing

**Local models**
- **Pros**: free, private, offline
- **Cons**: lower quality, requires resources
- **Best for**: development, privacy-sensitive data

### Model Selection

```env
# Groq models
AI_MODEL=llama-3.3-70b-versatile  # Recommended
AI_MODEL=llama3-70b-8192
AI_MODEL=mixtral-8x7b-32768
AI_MODEL=gemma2-9b-it

# OpenAI models
AI_MODEL=gpt-4                    # Best quality
AI_MODEL=gpt-4-turbo-preview      # Balanced
AI_MODEL=gpt-3.5-turbo            # Faster, cheaper

# Anthropic models
AI_MODEL=claude-3-opus-20240229    # Best quality
AI_MODEL=claude-3-sonnet-20240229  # Balanced
AI_MODEL=claude-3-haiku-20240307   # Fast
```

> **Note:** the OpenAI and Anthropic model IDs above may be outdated by the time you read this — check each provider's current model list before deploying.

## API Reference

### Jobs API

**List jobs**

```http
GET /api/jobs/
```

Parameters:
| Parameter    | Description        |
|--------------|---------------------|
| `search`     | Search query        |
| `location`   | Filter by location  |
| `is_remote`  | `true` or `false`   |
| `min_salary` | Minimum salary      |
| `page`       | Page number         |
| `ordering`   | Sort field          |

**Get job details**

```http
GET /api/jobs/{id}/
```

**Evaluate jobs**

```http
POST /api/evaluate-jobs/
```

```json
{
  "job_ids": [1, 2, 3],
  "use_ai": true
}
```

### AI API

**Analyze job**

```http
GET /api/ai-analyze/{job_id}/
```

**Regenerate analysis**

```http
POST /api/regenerate-analysis/{job_id}/
```

### Preferences API

**Get preferences**

```http
GET /api/preferences/
```

**Update preferences**

```http
POST /api/preferences/
```

```json
{
  "remote_only": true,
  "include_keywords": ["python", "django"],
  "preferred_locations": ["Remote"]
}
```

## Troubleshooting

### 1. Database Connection Errors

**Error:** `FATAL: Peer authentication failed`

```bash
# Fix: update pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Change: local   all   all   peer  →  local   all   all   md5
sudo systemctl restart postgresql
```

**Error:** `FATAL: database does not exist`

```bash
sudo -u postgres psql -c "CREATE DATABASE job_seeker OWNER jobuser;"
```

### 2. AI Provider Errors

**Error:** `GROQ_API_KEY not found`

```bash
# Check .env file
cat .env | grep GROQ_API_KEY
# Add: GROQ_API_KEY=gsk_your_key_here
```

**Error:** `Rate limit exceeded`

```bash
# Increase timeout and retries in .env
REQUEST_TIMEOUT=120
MAX_RETRIES=10
```

### 3. Job Fetching Errors

**Error:** `403 Forbidden`

```bash
# Update user agent in .env
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
```

**Error:** Timeout errors

```bash
# Increase timeout
REQUEST_TIMEOUT=120
```

### 4. Migration Errors

**Error:** `No migrations to apply`

```bash
python manage.py makemigrations
python manage.py migrate --fake-initial
```

### 5. Static Files Errors

**Error:** Static file not found

```bash
# Create static directory
mkdir -p static
# Collect static files
python manage.py collectstatic --noinput
```

### Logs

```bash
# Django logs
tail -f logs/debug.log

# Celery logs
celery -A job_seeker worker -l info

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Debug Mode

```bash
# Enable debug
DEBUG=True  # In .env

# Increase verbosity
python manage.py runserver --verbosity 3
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes
CREATE INDEX CONCURRENTLY idx_job_title ON jobs_job(title);
CREATE INDEX CONCURRENTLY idx_job_company ON jobs_job(company);
CREATE INDEX CONCURRENTLY idx_job_posted_date ON jobs_job(posted_date DESC);
```

### Cache Optimization

```bash
# Use Redis cache
REDIS_URL=redis://localhost:6379/1
CACHE_TTL=3600  # 1 hour
```

## Contributing

### Development Workflow

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/job_seeker.git
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```
4. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
5. Make your changes
6. Run tests:
   ```bash
   pytest
   ```
7. Submit a pull request

### Code Style

```bash
# Format code
black .

# Check style
flake8 .

# Sort imports
isort .
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific tests
python manage.py test tests.test_models
python manage.py test tests.test_services

# Run with coverage
pytest --cov=jobs tests/
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Django Community for the excellent framework
- Groq for fast AI inference
- OpenAI for GPT models
- Anthropic for Claude
- Google for Gemini
- All contributors who help improve this project

## Support

**Documentation**
- Official Documentation
- Project Wiki

**Community**
- Discord Server
- GitHub Discussions

**Bug Reports**
- GitHub Issues
- Email: support@jobseeker.com

## Quick Start Commands

### Linux/macOS

```bash
# Complete setup
./scripts/linux_setup.sh

# Run server
python manage.py runserver

# Process jobs
python manage.py process_jobs --all

# Start Celery
celery -A job_seeker worker -l info
```

### Windows

```powershell
# Complete setup
.\scripts\powershell_setup.ps1

# Run server
python manage.py runserver

# Process jobs
python manage.py process_jobs --all

# Start Celery
celery -A job_seeker worker -l info
```

### Docker

```bash
# Start all services
docker-compose up -d

# Process jobs
docker-compose exec web python manage.py process_jobs --all

# View logs
docker-compose logs -f web
```

---

🎉 **Congratulations!** You're now ready to use AI Job Seeker. Visit `http://localhost:8000` to start finding your perfect job matches with AI-powered recommendations.