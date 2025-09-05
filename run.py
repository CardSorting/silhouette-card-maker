#!/usr/bin/env python3
"""
Main entry point for the Silhouette Card Maker Flask application.
Refactored with blueprints for better organization.
"""

import os
from dotenv import load_dotenv
from app import create_app
from flask import flash, redirect, url_for

# Load environment variables from .env file
load_dotenv()

app = create_app()


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum file size is 64MB.')
    return redirect(url_for('main.index'))


@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('main.index'))


if __name__ == '__main__':
    # Get configuration from environment
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    if not debug:
        print("⚠️  WARNING: This is a development server!")
        print("⚠️  Do not use it in a production deployment.")
        print("⚠️  Use a production WSGI server instead.")
        print("")
        print("🚀 For production deployment, use:")
        print("   gunicorn -c gunicorn.conf.py start_production:app")
        print("   docker-compose up -d")
        print("   ./deploy.sh")
        print("")
    
    app.run(debug=debug, host=host, port=port)