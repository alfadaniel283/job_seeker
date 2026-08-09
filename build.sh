#!/bin/bash
# build.sh - Render build script

echo "🚀 Starting build process..."

# Exit on any error
set -e

# Install Python dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

#Creating superuser in app
python manage.py create_admin

echo "✅ Build complete!"