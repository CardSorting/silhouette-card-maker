#!/bin/bash

# Start the application with PostgreSQL configuration
# This script sets the correct environment variables for PostgreSQL connection

echo "🚀 Starting Silhouette Card Maker with PostgreSQL..."

# Set PostgreSQL connection parameters
export DB_HOST="108.175.14.173"
export DB_PORT="5432"
export DB_NAME="dream_"
export DB_USER="dreambees"
export DB_PASSWORD="Zy2H%@sg0Ykl6ngf"

# Set Flask environment
export FLASK_ENV="development"
export FLASK_APP="run.py"

echo "✅ Environment variables set:"
echo "   DB_HOST: $DB_HOST"
echo "   DB_PORT: $DB_PORT"
echo "   DB_NAME: $DB_NAME"
echo "   DB_USER: $DB_USER"
echo "   DB_PASSWORD: [HIDDEN]"
echo "   FLASK_ENV: $FLASK_ENV"
echo ""

# Test database connection first
echo "🔍 Testing database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        database='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD'
    )
    print('✅ Database connection successful!')
    conn.close()
except Exception as e:
    print('❌ Database connection failed:', e)
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Starting Flask application..."
    echo "   Access the application at: http://localhost:5000"
    echo "   Press Ctrl+C to stop the server"
    echo ""
    python3 run.py
else
    echo "❌ Failed to start application due to database connection error"
    exit 1
fi
