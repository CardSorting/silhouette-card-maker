#!/bin/bash

# Production deployment script for Silhouette Card Maker API

set -e

echo "🚀 Starting production deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="silhouette-card-maker"
APP_DIR="/opt/silhouette-card-maker"
SERVICE_USER="www-data"
PYTHON_VERSION="3.10"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
print_status "Initializing database..."
DATABASE_URL=sqlite:///app.db python migrate.py init

# Set up environment variables
print_status "Setting up environment variables..."
if [ ! -f ".env" ]; then
    print_warning "Creating .env file from template..."
    cp config.env.example .env
    print_warning "Please edit .env file with your production settings!"
fi

# Test the application
print_status "Testing application..."
python start_production.py &
APP_PID=$!
sleep 5

# Test health endpoint
if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
    print_status "Application test successful!"
    kill $APP_PID
else
    print_error "Application test failed!"
    kill $APP_PID
    exit 1
fi

# Create systemd service (optional)
if command -v systemctl &> /dev/null; then
    print_status "Creating systemd service..."
    sudo cp silhouette-card-maker.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable silhouette-card-maker
    print_status "Service created. Start with: sudo systemctl start silhouette-card-maker"
fi

# Docker deployment (optional)
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    print_status "Docker deployment available. Run: docker-compose up -d"
fi

print_status "Deployment completed successfully!"
print_status "To start the application:"
print_status "  Development: python run.py"
print_status "  Production:  gunicorn -c gunicorn.conf.py start_production:app"
print_status "  Docker:      docker-compose up -d"
print_status "  Service:     sudo systemctl start silhouette-card-maker"

echo ""
print_warning "Don't forget to:"
print_warning "1. Edit .env file with your production settings"
print_warning "2. Set up SSL certificates for HTTPS"
print_warning "3. Configure your firewall"
print_warning "4. Set up monitoring and logging"
