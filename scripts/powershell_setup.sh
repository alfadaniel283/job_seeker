# ============================================
# AI Job Seeker - Complete Setup Script (Windows)
# ============================================

# Colors for output
$GREEN = "Green"
$RED = "Red"
$YELLOW = "Yellow"
$BLUE = "Cyan"

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $GREEN
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $RED
}

function Write-Info {
    param([string]$Message)
    Write-Host "→ $Message" -ForegroundColor $YELLOW
}

function Write-Header {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor $BLUE
}

Clear-Host
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Host "AI Job Seeker - Complete Setup Script" -ForegroundColor $BLUE
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Host ""

# ============================================
# CHECK PYTHON VERSION
# ============================================
Write-Info "Checking Python version..."

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+\.\d+)") {
        $version = [version]$Matches[1]
        if ($version -ge [version]"3.10") {
            Write-Success "Python $($version.ToString()) detected"
        } else {
            Write-Error "Python $($version.ToString()) detected. Python 3.10 or higher is required."
            Write-Host ""
            Write-Host "Please install Python 3.10 or higher from: https://www.python.org/downloads/"
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
} catch {
    Write-Error "Python 3 not found. Please install Python 3.10 or higher."
    Write-Host ""
    Write-Host "Download Python from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================
# CHECK POSTGRESQL
# ============================================
Write-Info "Checking PostgreSQL installation..."

$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlPath) {
    Write-Success "PostgreSQL found at: $($psqlPath.Source)"
    $usePostgres = $true
} else {
    Write-Info "PostgreSQL not found. Will use SQLite instead."
    Write-Info "To use PostgreSQL, download from: https://www.postgresql.org/download/windows/"
    $usePostgres = $false
}

# ============================================
# CREATE VIRTUAL ENVIRONMENT
# ============================================
Write-Info "Creating virtual environment..."

if (Test-Path ".venv") {
    Write-Info "Virtual environment already exists (skipping)"
} else {
    python -m venv .venv
    if (Test-Path ".venv") {
        Write-Success "Virtual environment created"
    } else {
        Write-Error "Failed to create virtual environment"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate virtual environment
Write-Info "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# ============================================
# INSTALL DEPENDENCIES
# ============================================
Write-Info "Installing dependencies..."

python -m pip install --upgrade pip | Out-Null

if (Test-Path "requirements.txt") {
    pip install -r requirements.txt | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed"
    } else {
        Write-Error "Failed to install dependencies"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Info "requirements.txt not found, installing base packages..."
    pip install django djangorestframework django-cors-headers python-dotenv psycopg2-binary requests beautifulsoup4 lxml | Out-Null
    pip freeze > requirements.txt
    Write-Success "Base packages installed and requirements.txt created"
}

# ============================================
# CREATE DIRECTORY STRUCTURE
# ============================================
Write-Info "Creating directory structure..."

$directories = @(
    "logs",
    "media",
    "static",
    "static\css",
    "static\js",
    "static\images",
    "data",
    "models",
    "jobs\migrations",
    "jobs\templates\jobs",
    "jobs\static\jobs\css",
    "jobs\static\jobs\js",
    "jobs\services\ai_providers",
    "jobs\management\commands",
    "tests",
    "scripts"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created directory: $dir"
    } else {
        Write-Info "Directory already exists: $dir (skipping)"
    }
}

# Create __init__.py files
Write-Info "Creating Python package files..."

$packageFiles = @(
    "jobs\__init__.py",
    "jobs\services\__init__.py",
    "jobs\services\ai_providers\__init__.py",
    "jobs\management\__init__.py",
    "jobs\management\commands\__init__.py",
    "tests\__init__.py"
)

foreach ($file in $packageFiles) {
    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file -Force | Out-Null
        Write-Success "Created: $file"
    }
}

# ============================================
# CREATE .ENV FILE
# ============================================
Write-Info "Setting up environment variables..."

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Success ".env file created from example"
    } else {
        $secretKey = python -c "import secrets; print(secrets.token_urlsafe(50))"
        
        @"
# ============================================
# DJANGO CORE SETTINGS
# ============================================
DJANGO_SECRET_KEY=$secretKey
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

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
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=

# ============================================
# AI PROVIDER SELECTION
# ============================================
AI_PROVIDER_PREFERENCE=groq
AI_MODEL=llama-3.3-70b-versatile
AI_EMBEDDING_MODEL=text-embedding-ada-002
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=2000

# ============================================
# JOB FETCHING SETTINGS
# ============================================
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
REQUEST_TIMEOUT=120
MAX_RETRIES=10
CACHE_TTL=3600

# ============================================
# LOGGING SETTINGS
# ============================================
LOG_LEVEL=INFO

# ============================================
# FEATURE FLAGS
# ============================================
AI_DUPLICATE_DETECTION=True
AI_JOB_ENRICHMENT=True
AUTO_EVALUATE_JOBS=True
USE_LOCAL_AI=False

# ============================================
# PERFORMANCE SETTINGS
# ============================================
BATCH_SIZE=100
WORKER_CONCURRENCY=4
RATE_LIMIT=60
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Success ".env file created with generated secret key"
    }
} else {
    Write-Info ".env file already exists (skipping)"
}

# ============================================
# DATABASE SETUP
# ============================================
Write-Header "Setting up database"

if ($usePostgres) {
    Write-Info "Configuring PostgreSQL..."
    
    # Load .env
    Get-Content .env | ForEach-Object {
        if ($_ -match "^(DB_USER|DB_PASS|DB_NAME|DB_HOST|DB_PORT)=") {
            $var = $_ -split "="
            Set-Variable -Name $var[0] -Value $var[1] -Scope Global
        }
    }
    
    # Check if database exists and create if needed
    $dbExists = psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>$null
    if ($dbExists -ne "1") {
        Write-Info "Creating database: $DB_NAME"
        psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>$null
        psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>$null
        psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>$null
        Write-Success "Database '$DB_NAME' created"
    } else {
        Write-Info "Database '$DB_NAME' already exists"
    }
} else {
    Write-Info "Using SQLite (no database setup needed)"
    # Update .env to use SQLite
    (Get-Content .env) -replace 'DATABASE_URL=.*', 'DATABASE_URL=sqlite:///db.sqlite3' | Set-Content .env
}

# ============================================
# DJANGO SETUP
# ============================================
Write-Header "Setting up Django"

# Check if Django project exists
if (-not (Test-Path "manage.py")) {
    Write-Info "Creating Django project..."
    django-admin startproject job_seeker .
    Write-Success "Django project created"
} else {
    Write-Info "Django project already exists"
}

# Check if jobs app exists
if (-not (Test-Path "jobs")) {
    Write-Info "Creating jobs app..."
    python manage.py startapp jobs
    Write-Success "Jobs app created"
} else {
    Write-Info "Jobs app already exists"
}

# Create logs directory and file
Write-Info "Setting up logging..."
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
New-Item -ItemType File -Path "logs\debug.log" -Force | Out-Null

# ============================================
# RUN MIGRATIONS
# ============================================
Write-Info "Running database migrations..."
python manage.py makemigrations | Out-Null
python manage.py migrate | Out-Null
Write-Success "Database migrations completed"

# ============================================
# CREATE SUPERUSER
# ============================================
Write-Info "Creating superuser..."
try {
    python manage.py createsuperuser --noinput --username=admin --email=admin@example.com 2>$null
} catch {
    Write-Info "Superuser already exists or creation skipped"
}

# ============================================
# COLLECT STATIC FILES
# ============================================
Write-Info "Collecting static files..."
python manage.py collectstatic --noinput | Out-Null
Write-Success "Static files collected"

# ============================================
# CREATE CELERY CONFIG
# ============================================
Write-Info "Setting up Celery..."

if (-not (Test-Path "job_seeker\celery.py")) {
    @"
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_seeker.settings')

app = Celery('job_seeker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
"@ | Out-File -FilePath "job_seeker\celery.py" -Encoding UTF8
    Write-Success "Celery configured"
}

# Update __init__.py for Celery
if (Test-Path "job_seeker\__init__.py") {
    $initContent = Get-Content "job_seeker\__init__.py" -Raw
    if ($initContent -notmatch "celery_app") {
        @"
from .celery import app as celery_app

__all__ = ('celery_app',)
"@ | Out-File -FilePath "job_seeker\__init__.py" -Encoding UTF8 -Append
        Write-Success "Updated __init__.py for Celery"
    }
}

# ============================================
# FINAL MESSAGE
# ============================================
Write-Host ""
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Success "Setup Complete!"
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Host ""
Write-Host "📋 Summary:" -ForegroundColor $YELLOW
Write-Host "  ✅ Python $($version.ToString())"
Write-Host "  ✅ Virtual environment created"
Write-Host "  ✅ Dependencies installed"
Write-Host "  ✅ Database configured"
Write-Host "  ✅ Django project ready"
Write-Host "  ✅ Superuser created (admin)"
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor $YELLOW
Write-Host "1. Edit .env file and add your AI API keys:"
Write-Host "   notepad .env"
Write-Host ""
Write-Host "2. Activate virtual environment (if not already):"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "3. Start the development server:"
Write-Host "   python manage.py runserver"
Write-Host ""
Write-Host "4. Start Celery worker (in a new terminal):"
Write-Host "   celery -A job_seeker worker -l info"
Write-Host ""
Write-Host "5. Start Redis (if using Celery):"
Write-Host "   redis-server"
Write-Host ""
Write-Host "🔑 Default admin credentials:" -ForegroundColor $GREEN
Write-Host "   Username: admin"
Write-Host "   Password: (set during creation)"
Write-Host ""
Write-Host "🌐 Visit: http://localhost:8000" -ForegroundColor $BLUE
Write-Host "=========================================" -ForegroundColor $BLUE

Read-Host "`nPress Enter to exit"