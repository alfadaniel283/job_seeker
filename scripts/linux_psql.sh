#!/bin/bash

echo "========================================="
echo "PostgreSQL Database Setup for Job Seeker"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_header() { echo -e "${BLUE}==> $1${NC}"; }

# Load .env file if exists
if [ -f ".env" ]; then
    source .env
fi

# Default values
DB_USER=${DB_USER:-"jobuser"}
DB_PASS=${DB_PASS:-"jobpass"}
DB_NAME=${DB_NAME:-"job_seeker"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}

print_header "Database Configuration"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST:$DB_PORT"
echo ""

# ============================================
# CHECK POSTGRESQL INSTALLATION
# ============================================
print_info "Checking PostgreSQL installation..."

if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed!"
    echo ""
    echo "Please install PostgreSQL first:"
    echo "  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "  macOS: brew install postgresql"
    echo "  Windows: Download from https://www.postgresql.org/download/windows/"
    exit 1
fi
print_success "PostgreSQL found"

# ============================================
# CHECK POSTGRESQL SERVICE
# ============================================
print_info "Checking PostgreSQL service..."

if ! pg_isready -h $DB_HOST -p $DB_PORT &> /dev/null; then
    print_info "PostgreSQL is not running. Starting..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl start postgresql
        sleep 3
    elif command -v brew &> /dev/null; then
        brew services start postgresql
        sleep 3
    else
        print_error "Unable to start PostgreSQL automatically"
        echo "Please start PostgreSQL manually and run this script again"
        exit 1
    fi
fi

if pg_isready -h $DB_HOST -p $DB_PORT &> /dev/null; then
    print_success "PostgreSQL is running"
else
    print_error "PostgreSQL is not responding"
    exit 1
fi

# ============================================
# CREATE USER
# ============================================
print_info "Setting up database user..."

# Check if user exists
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    print_info "User '$DB_USER' already exists"
else
    print_info "Creating user '$DB_USER'..."
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "User '$DB_USER' created successfully"
    else
        print_error "Failed to create user '$DB_USER'"
        exit 1
    fi
fi

# ============================================
# CREATE DATABASE
# ============================================
print_info "Setting up database..."

# Check if database exists
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    print_info "Database '$DB_NAME' already exists"
else
    print_info "Creating database '$DB_NAME'..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Database '$DB_NAME' created successfully"
    else
        print_error "Failed to create database '$DB_NAME'"
        exit 1
    fi
fi

# ============================================
# GRANT PRIVILEGES
# ============================================
print_info "Granting privileges..."

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"

print_success "Privileges granted"

# ============================================
# TEST CONNECTION
# ============================================
print_info "Testing database connection..."

if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    print_success "Connection successful!"
else
    print_error "Connection failed!"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check pg_hba.conf: sudo grep -r 'local.*all.*peer' /etc/postgresql/*/main/pg_hba.conf"
    echo "2. Update to: local   all             all                                     md5"
    echo "3. Restart PostgreSQL: sudo systemctl restart postgresql"
    echo "4. Check if user exists: sudo -u postgres psql -c \"\\du\""
    echo "5. Check if database exists: sudo -u postgres psql -c \"\\l\""
    exit 1
fi

# ============================================
# UPDATE .ENV FILE
# ============================================
print_info "Updating .env file..."

if [ -f ".env" ]; then
    # Update .env with database settings
    sed -i "s/^DB_USER=.*/DB_USER=$DB_USER/" .env
    sed -i "s/^DB_PASS=.*/DB_PASS=$DB_PASS/" .env
    sed -i "s/^DB_NAME=.*/DB_NAME=$DB_NAME/" .env
    sed -i "s/^DB_HOST=.*/DB_HOST=$DB_HOST/" .env
    sed -i "s/^DB_PORT=.*/DB_PORT=$DB_PORT/" .env
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME|" .env
    print_success ".env file updated"
else
    # Create .env file
    cat > .env << EOL
# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME
DB_USER=$DB_USER
DB_PASS=$DB_PASS
DB_NAME=$DB_NAME
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT

# Django Settings
DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# AI Settings (Add your keys)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
AI_PROVIDER_PREFERENCE=groq
AI_MODEL=llama-3.3-70b-versatile
EOL
    print_success ".env file created"
fi

# ============================================
# RUN DJANGO MIGRATIONS
# ============================================
if [ -f "manage.py" ]; then
    print_info "Running Django migrations..."
    python manage.py makemigrations > /dev/null 2>&1
    python manage.py migrate > /dev/null 2>&1
    print_success "Django migrations completed"
else
    print_info "manage.py not found. Run setup.sh first or run migrations manually."
fi

# ============================================
# FINAL MESSAGE
# ============================================
echo ""
echo "========================================="
echo -e "${GREEN}✅ Database Setup Complete!${NC}"
echo "========================================="
echo ""
echo -e "${YELLOW}📋 Database Information:${NC}"
echo "  Name: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASS"
echo "  Host: $DB_HOST:$DB_PORT"
echo ""
echo "Connection String:"
echo "  postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Add your AI API keys to .env:"
echo "   nano .env"
echo ""
echo "2. Start the development server:"
echo "   python manage.py runserver"
echo ""
echo "3. Test database connection:"
echo "   PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
echo ""
echo -e "${GREEN}🎯 Database is ready for Job Seeker!${NC}"
echo "========================================="