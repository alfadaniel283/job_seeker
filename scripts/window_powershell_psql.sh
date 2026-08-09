# ============================================
# PostgreSQL Database Setup for Job Seeker (Windows)
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
Write-Host "PostgreSQL Database Setup for Job Seeker" -ForegroundColor $BLUE
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Host ""

# ============================================
# LOAD .ENV FILE
# ============================================
if (Test-Path ".env") {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^(DB_USER|DB_PASS|DB_NAME|DB_HOST|DB_PORT)=") {
            $var = $_ -split "="
            Set-Variable -Name $var[0] -Value $var[1] -Scope Global
        }
    }
}

# Default values
if (-not $DB_USER) { $DB_USER = "jobuser" }
if (-not $DB_PASS) { $DB_PASS = "jobpass" }
if (-not $DB_NAME) { $DB_NAME = "job_seeker" }
if (-not $DB_HOST) { $DB_HOST = "localhost" }
if (-not $DB_PORT) { $DB_PORT = "5432" }

Write-Header "Database Configuration"
Write-Host "  Database: $DB_NAME"
Write-Host "  User: $DB_USER"
Write-Host "  Host: $DB_HOST`:$DB_PORT"
Write-Host ""

# ============================================
# CHECK POSTGRESQL INSTALLATION
# ============================================
Write-Info "Checking PostgreSQL installation..."

$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Error "PostgreSQL is not installed!"
    Write-Host ""
    Write-Host "Please install PostgreSQL from:"
    Write-Host "  https://www.postgresql.org/download/windows/"
    Write-Host ""
    Write-Host "Or use SQLite by setting DATABASE_URL=sqlite:///db.sqlite3 in .env"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Success "PostgreSQL found at: $($psqlPath.Source)"

# ============================================
# CHECK POSTGRESQL SERVICE
# ============================================
Write-Info "Checking PostgreSQL service..."

$serviceName = "postgresql*"
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $service) {
    Write-Error "PostgreSQL service not found!"
    Write-Host ""
    Write-Host "Please start PostgreSQL manually or reinstall."
    Read-Host "Press Enter to exit"
    exit 1
}

if ($service.Status -ne "Running") {
    Write-Info "Starting PostgreSQL service..."
    Start-Service -Name $service.Name
    Start-Sleep -Seconds 5
}

if ((Get-Service -Name $service.Name).Status -eq "Running") {
    Write-Success "PostgreSQL is running"
} else {
    Write-Error "PostgreSQL is not running!"
    Write-Host ""
    Write-Host "Try starting manually: Start-Service $($service.Name)"
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================
# CREATE USER
# ============================================
Write-Info "Setting up database user..."

# Check if user exists
$userExists = psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>$null
if ($userExists -eq "1") {
    Write-Info "User '$DB_USER' already exists"
} else {
    Write-Info "Creating user '$DB_USER'..."
    psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "User '$DB_USER' created successfully"
    } else {
        Write-Error "Failed to create user '$DB_USER'"
        Write-Host ""
        Write-Host "Try running with PostgreSQL admin password:"
        Write-Host "  psql -U postgres -c 'CREATE USER $DB_USER WITH PASSWORD ''$DB_PASS'';'"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ============================================
# CREATE DATABASE
# ============================================
Write-Info "Setting up database..."

# Check if database exists
$dbExists = psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>$null
if ($dbExists -eq "1") {
    Write-Info "Database '$DB_NAME' already exists"
} else {
    Write-Info "Creating database '$DB_NAME'..."
    psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Database '$DB_NAME' created successfully"
    } else {
        Write-Error "Failed to create database '$DB_NAME'"
        Write-Host ""
        Write-Host "Try running with PostgreSQL admin password:"
        Write-Host "  psql -U postgres -c 'CREATE DATABASE $DB_NAME OWNER $DB_USER;'"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ============================================
# GRANT PRIVILEGES
# ============================================
Write-Info "Granting privileges..."

psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>$null
psql -U postgres -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>$null
psql -U postgres -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" 2>$null
psql -U postgres -d $DB_NAME -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" 2>$null

Write-Success "Privileges granted"

# ============================================
# TEST CONNECTION
# ============================================
Write-Info "Testing database connection..."

$env:PGPASSWORD = $DB_PASS
$connectionTest = psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" 2>&1
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Success "Connection successful!"
} else {
    Write-Error "Connection failed!"
    Write-Host ""
    Write-Host "Troubleshooting:"
    Write-Host "1. Check PostgreSQL is running"
    Write-Host "2. Check pg_hba.conf for authentication settings"
    Write-Host "3. Check if user exists: psql -U postgres -c 'SELECT * FROM pg_roles;'"
    Write-Host "4. Check if database exists: psql -U postgres -c 'SELECT * FROM pg_database;'"
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================
# UPDATE .ENV FILE
# ============================================
Write-Info "Updating .env file..."

if (Test-Path ".env") {
    # Read current .env content
    $envContent = Get-Content ".env" -Raw
    
    # Update or add database settings
    $envContent = $envContent -replace '^DB_USER=.*', "DB_USER=$DB_USER"
    $envContent = $envContent -replace '^DB_PASS=.*', "DB_PASS=$DB_PASS"
    $envContent = $envContent -replace '^DB_NAME=.*', "DB_NAME=$DB_NAME"
    $envContent = $envContent -replace '^DB_HOST=.*', "DB_HOST=$DB_HOST"
    $envContent = $envContent -replace '^DB_PORT=.*', "DB_PORT=$DB_PORT"
    $envContent = $envContent -replace '^DATABASE_URL=.*', "DATABASE_URL=postgresql://$DB_USER`:$DB_PASS@$DB_HOST`:$DB_PORT/$DB_NAME"
    
    # If any settings don't exist, add them
    if ($envContent -notmatch '^DB_USER=') {
        $envContent += "`nDB_USER=$DB_USER"
    }
    if ($envContent -notmatch '^DB_PASS=') {
        $envContent += "`nDB_PASS=$DB_PASS"
    }
    if ($envContent -notmatch '^DB_NAME=') {
        $envContent += "`nDB_NAME=$DB_NAME"
    }
    if ($envContent -notmatch '^DB_HOST=') {
        $envContent += "`nDB_HOST=$DB_HOST"
    }
    if ($envContent -notmatch '^DB_PORT=') {
        $envContent += "`nDB_PORT=$DB_PORT"
    }
    if ($envContent -notmatch '^DATABASE_URL=') {
        $envContent += "`nDATABASE_URL=postgresql://$DB_USER`:$DB_PASS@$DB_HOST`:$DB_PORT/$DB_NAME"
    }
    
    # Save updated .env
    $envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force
    Write-Success ".env file updated"
} else {
    # Create new .env file
    $secretKey = python -c "import secrets; print(secrets.token_urlsafe(50))" 2>$null
    if (-not $secretKey) {
        $secretKey = "your-secret-key-here"
    }
    
    @"
# Database Configuration
DATABASE_URL=postgresql://$DB_USER`:$DB_PASS@$DB_HOST`:$DB_PORT/$DB_NAME
DB_USER=$DB_USER
DB_PASS=$DB_PASS
DB_NAME=$DB_NAME
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT

# Django Settings
DJANGO_SECRET_KEY=$secretKey
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI Settings (Add your keys)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
AI_PROVIDER_PREFERENCE=groq
AI_MODEL=llama-3.3-70b-versatile
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success ".env file created"
}

# ============================================
# RUN DJANGO MIGRATIONS
# ============================================
if (Test-Path "manage.py") {
    Write-Info "Running Django migrations..."
    python manage.py makemigrations 2>$null
    python manage.py migrate 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Django migrations completed"
    } else {
        Write-Error "Django migrations failed"
        Write-Host ""
        Write-Host "Try running manually:"
        Write-Host "  python manage.py makemigrations"
        Write-Host "  python manage.py migrate"
    }
} else {
    Write-Info "manage.py not found. Run setup.sh first or run migrations manually."
}

# ============================================
# FINAL MESSAGE
# ============================================
Write-Host ""
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Success "Database Setup Complete!"
Write-Host "=========================================" -ForegroundColor $BLUE
Write-Host ""
Write-Host "📋 Database Information:" -ForegroundColor $YELLOW
Write-Host "  Name: $DB_NAME"
Write-Host "  User: $DB_USER"
Write-Host "  Password: $DB_PASS"
Write-Host "  Host: $DB_HOST`:$DB_PORT"
Write-Host ""
Write-Host "Connection String:"
Write-Host "  postgresql://$DB_USER`:$DB_PASS@$DB_HOST`:$DB_PORT/$DB_NAME"
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor $YELLOW
Write-Host "1. Add your AI API keys to .env:"
Write-Host "   notepad .env"
Write-Host ""
Write-Host "2. Activate virtual environment:"
Write-Host "   .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "3. Start the development server:"
Write-Host "   python manage.py runserver"
Write-Host ""
Write-Host "4. Test database connection:"
Write-Host "   set PGPASSWORD=$DB_PASS`; psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
Write-Host ""
Write-Host "🎯 Database is ready for Job Seeker!" -ForegroundColor $GREEN
Write-Host "=========================================" -ForegroundColor $BLUE

Read-Host "`nPress Enter to exit"