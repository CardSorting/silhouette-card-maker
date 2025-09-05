#!/usr/bin/env python3
"""
Production startup script for the Silhouette Card Maker API.
This script sets up the application for production deployment with Gunicorn.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set production environment
os.environ['FLASK_ENV'] = 'production'

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from app import create_app

# Create the application
app = create_app()

if __name__ == '__main__':
    # This is for development/testing only
    # In production, use: gunicorn -c gunicorn.conf.py start_production:app
    app.run(debug=False, host='0.0.0.0', port=5000)
