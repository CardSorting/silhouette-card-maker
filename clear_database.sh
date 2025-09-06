#!/bin/bash

# Database Clearing Script for Silhouette Card Maker
# This script clears the PostgreSQL database completely

set -e  # Exit on any error

echo "🧹 PostgreSQL Database Clearing Script"
echo "======================================"

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

# Check if PostgreSQL dependencies are installed
if ! python3 -c "import psycopg2" 2>/dev/null; then
    print_status "Installing PostgreSQL dependencies..."
    pip3 install psycopg2-binary==2.9.9
    
    if [ $? -eq 0 ]; then
        print_success "PostgreSQL dependencies installed successfully"
    else
        print_error "Failed to install PostgreSQL dependencies"
        exit 1
    fi
fi

# Clear the database
print_status "Clearing PostgreSQL database..."
python3 clear_postgresql.py

if [ $? -eq 0 ]; then
    print_success "Database cleared successfully!"
    echo ""
    echo "The PostgreSQL database has been completely cleared."
    echo "You can now run a fresh migration with:"
    echo "  ./migrate.sh"
    echo ""
    echo "Or initialize a fresh database with:"
    echo "  python3 init_postgresql.py"
    echo ""
else
    print_error "Failed to clear database"
    exit 1
fi
