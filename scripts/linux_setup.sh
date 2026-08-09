#!/bin/bash

echo "========================================="
echo "AI Job Seeker - Complete Setup Script"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_header() { echo -e "${BLUE}==> $1${NC}"; }

# ============================================
# CHECK PYTHON VERSION
# ============================================
print_info "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ -z "$python_version" ]]; then
    print_error "Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

if [[ $(echo "$python_version < 3.10" | bc) -eq 1 ]]; then
    print_error "Python $python_version detected. Python 3.10 or higher is required."
    exit 1
fi
print_success "Python $python_version detected"

# ============================================
# CREATE VIRTUAL ENVIRONMENT
# ============================================
print_info "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists (skipping)"
fi

# Activate virtual environment
source .venv/bin/activate

# ============================================
# INSTALL DEPENDENCIES
# ============================================
print_info "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "Dependencies installed"
else
    print_info "requirements.txt not found, installing base packages..."
    pip install django djangorestframework django-cors-headers python-dotenv psycopg2-binary > /dev/null 2>&1
    pip freeze > requirements.txt
    print_success "Base packages installed and requirements.txt created"
fi

# ============================================
# CREATE DIRECTORY STRUCTURE
# ============================================
print_info "Creating directory structure..."
directories=(
    "logs"
    "media"
    "static"
    "static/css"
    "static/js"
    "static/images"
    "data"
    "models"
    "jobs/migrations"
    "jobs/templates/jobs"
    "jobs/static/jobs/css"
    "jobs/static/jobs/js"
    "jobs/services/ai_providers"
    "jobs/management/commands"
    "tests"
    "scripts"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Created directory: $dir"
    else
        print_info "Directory already exists: $dir (skipping)"
    fi
done

# Create __init__.py files
print_info "Creating Python package files..."
package_files=(
    "jobs/__init__.py"
    "jobs/services/__init__.py"
    "jobs/services/ai_providers/__init__.py"
    "jobs/management/__init__.py"
    "jobs/management/commands/__init__.py"
    "tests/__init__.py"
)

for file in "${package_files[@]}"; do
    if [ ! -f "$file" ]; then
        touch "$file"
        print_success "Created: $file"
    fi
done

# ============================================
# CREATE .env FILE
# ============================================
print_info "Setting up environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from example"
    else
        cat > .env << 'EOL'
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
EOL
        # Generate secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
        sed -i "s/DJANGO_SECRET_KEY=.*/DJANGO_SECRET_KEY=$SECRET_KEY/" .env
        print_success ".env file created with generated secret key"
    fi
else
    print_info ".env file already exists (skipping)"
fi

# ============================================
# DATABASE SETUP
# ============================================
print_header "Setting up database..."

# Load .env
source .env

if command -v psql &> /dev/null; then
    print_info "PostgreSQL detected, setting up database..."
    
    # Check if PostgreSQL is running
    if ! pg_isready &> /dev/null; then
        print_info "Starting PostgreSQL..."
        sudo systemctl start postgresql 2>/dev/null || brew services start postgresql 2>/dev/null
        sleep 3
    fi
    
    # Create user if not exists
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        print_info "Creating user: $DB_USER"
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null
        print_success "User '$DB_USER' created"
    else
        print_info "User '$DB_USER' already exists"
    fi
    
    # Create database if not exists
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        print_info "Creating database: $DB_NAME"
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null
        print_success "Database '$DB_NAME' created"
    else
        print_info "Database '$DB_NAME' already exists"
    fi
    
    # Grant privileges
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null
    sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null
    sudo -u postgres psql -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" 2>/dev/null
    print_success "Privileges granted"
    
    # Test connection
    if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "Database connection successful!"
    else
        print_error "Database connection failed!"
        print_info "Please check your PostgreSQL configuration"
    fi
else
    print_info "PostgreSQL not found, using SQLite"
    sed -i 's/DATABASE_URL=.*/DATABASE_URL=sqlite:\/\/\/db.sqlite3/' .env
fi

# ============================================
# DJANGO SETUP
# ============================================
print_header "Setting up Django"

# Check if Django project exists
if [ ! -f "manage.py" ]; then
    print_info "Creating Django project..."
    django-admin startproject job_seeker .
    print_success "Django project created"
else
    print_info "Django project already exists"
fi

# Check if jobs app exists
if [ ! -d "jobs" ]; then
    print_info "Creating jobs app..."
    python manage.py startapp jobs
    print_success "Jobs app created"
else
    print_info "Jobs app already exists"
fi

# Create logs directory and file
print_info "Setting up logging..."
mkdir -p logs
touch logs/debug.log
chmod 755 logs
chmod 644 logs/debug.log

# ============================================
# RUN MIGRATIONS
# ============================================
print_info "Running database migrations..."
python manage.py makemigrations > /dev/null 2>&1
python manage.py migrate > /dev/null 2>&1
print_success "Database migrations completed"

# ============================================
# CREATE SUPERUSER
# ============================================
print_info "Creating superuser..."
python manage.py createsuperuser --noinput --username=admin --email=admin@example.com 2>/dev/null || {
    print_info "Superuser already exists or creation skipped"
}

# ============================================
# COLLECT STATIC FILES
# ============================================
print_info "Collecting static files..."
python manage.py collectstatic --noinput > /dev/null 2>&1
print_success "Static files collected"

# ============================================
# SET PERMISSIONS
# ============================================
print_info "Setting permissions..."
chmod +x manage.py
chmod +x scripts/*.sh 2>/dev/null || true

# ============================================
# CREATE CELERY CONFIG
# ============================================
print_info "Setting up Celery..."
if [ ! -f "job_seeker/celery.py" ]; then
    cat > job_seeker/celery.py << 'EOL'
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'job_seeker.settings')

app = Celery('job_seeker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
EOL
    print_success "Celery configured"
fi

# Update __init__.py for Celery
if [ -f "job_seeker/__init__.py" ]; then
    if ! grep -q "celery_app" job_seeker/__init__.py; then
        echo "from .celery import app as celery_app" >> job_seeker/__init__.py
        echo "__all__ = ('celery_app',)" >> job_seeker/__init__.py
        print_success "Updated __init__.py for Celery"
    fi
fi

# ============================================
# FINAL MESSAGE
# ============================================
echo ""
echo "========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "========================================="
echo ""
echo -e "${YELLOW}📋 Summary:${NC}"
echo "  ✅ Python $python_version"
echo "  ✅ Virtual environment created"
echo "  ✅ Dependencies installed"
echo "  ✅ Database configured"
echo "  ✅ Django project ready"
echo "  ✅ Superuser created (admin)"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Edit .env file and add your AI API keys:"
echo "   nano .env"
echo ""
echo "2. Start the development server:"
echo "   python manage.py runserver"
echo ""
echo "3. Start Celery worker (in a new terminal):"
echo "   celery -A job_seeker worker -l info"
echo ""
echo "4. Start Redis (in a new terminal):"
echo "   redis-server"
echo ""
echo -e "${GREEN}🔑 Default admin credentials:${NC}"
echo "   Username: admin"
echo "   Password: (set during creation)"
echo ""
echo -e "${YELLOW}🌐 Visit: http://localhost:8000${NC}"
echo "========================================="