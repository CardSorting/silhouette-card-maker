#!/bin/bash

# PostgreSQL Migration Script for Silhouette Card Maker
# This script automates the migration process from SQLite to PostgreSQL

set -e  # Exit on any error

echo "🚀 Starting PostgreSQL Migration for Silhouette Card Maker"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed or not in PATH"
    exit 1
fi

print_status "Installing PostgreSQL dependencies..."
pip3 install psycopg2-binary==2.9.9

if [ $? -eq 0 ]; then
    print_success "PostgreSQL dependencies installed successfully"
else
    print_error "Failed to install PostgreSQL dependencies"
    exit 1
fi

# Clear existing PostgreSQL database
print_status "Clearing existing PostgreSQL database..."
python3 clear_postgresql.py

if [ $? -eq 0 ]; then
    print_success "PostgreSQL database cleared successfully"
else
    print_error "Failed to clear PostgreSQL database"
    exit 1
fi

# Check if SQLite database exists
if [ -f "instance/app.db" ]; then
    print_status "Found existing SQLite database. Will migrate data."
    MIGRATE_DATA=true
else
    print_warning "No existing SQLite database found. Will perform fresh installation."
    MIGRATE_DATA=false
fi

# Initialize PostgreSQL database
print_status "Initializing PostgreSQL database..."
python3 init_postgresql.py

if [ $? -eq 0 ]; then
    print_success "PostgreSQL database initialized successfully"
else
    print_error "Failed to initialize PostgreSQL database"
    exit 1
fi

# Migrate data if SQLite database exists
if [ "$MIGRATE_DATA" = true ]; then
    print_status "Migrating data from SQLite to PostgreSQL..."
    python3 migrate_to_postgresql.py
    
    if [ $? -eq 0 ]; then
        print_success "Data migration completed successfully"
    else
        print_error "Data migration failed"
        exit 1
    fi
fi

# Test the migration
print_status "Testing PostgreSQL connection and functionality..."
python3 test_postgresql.py

if [ $? -eq 0 ]; then
    print_success "All tests passed! PostgreSQL is working correctly."
else
    print_error "Some tests failed. Please check the configuration."
    exit 1
fi

echo ""
echo "🎉 Migration completed successfully!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Update your environment variables if needed:"
echo "   export DATABASE_URL='postgresql://dreambees:Zy2H%@sg0Ykl6ngf@108.175.14.173:5432/dream_'"
echo ""
echo "2. Start the application:"
echo "   python3 run.py"
echo ""
echo "3. Or for production:"
echo "   gunicorn -c gunicorn.conf.py run:app"
echo ""
echo "4. Access the application at:"
echo "   http://localhost:5000"
echo ""
echo "5. Default admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo "   (Please change these in production!)"
echo ""
print_warning "Remember to change the default admin password in production!"
echo ""
print_success "Migration completed successfully! 🚀"
