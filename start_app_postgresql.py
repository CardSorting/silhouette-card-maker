#!/usr/bin/env python3
"""
Start the Flask application with PostgreSQL using the custom database engine.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Start the Flask application with PostgreSQL"""
    try:
        # Set PostgreSQL connection parameters
        os.environ['DB_HOST'] = '108.175.14.173'
        os.environ['DB_PORT'] = '5432'
        os.environ['DB_NAME'] = 'dream_'
        os.environ['DB_USER'] = 'dreambees'
        os.environ['DB_PASSWORD'] = 'Zy2H%@sg0Ykl6ngf'
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_APP'] = 'run.py'
        
        logger.info("🚀 Starting Silhouette Card Maker with PostgreSQL...")
        logger.info("✅ Environment variables set:")
        logger.info(f"   DB_HOST: {os.environ['DB_HOST']}")
        logger.info(f"   DB_PORT: {os.environ['DB_PORT']}")
        logger.info(f"   DB_NAME: {os.environ['DB_NAME']}")
        logger.info(f"   DB_USER: {os.environ['DB_USER']}")
        logger.info(f"   DB_PASSWORD: [HIDDEN]")
        logger.info(f"   FLASK_ENV: {os.environ['FLASK_ENV']}")
        
        # Test database connection first
        logger.info("🔍 Testing database connection...")
        from app.database import create_postgresql_engine
        from sqlalchemy import text
        
        engine = create_postgresql_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                logger.info("✅ Database connection successful!")
            else:
                logger.error("❌ Database connection failed!")
                return 1
        
        # Import and start the Flask app
        logger.info("🎉 Starting Flask application...")
        logger.info("   Access the application at: http://localhost:5000")
        logger.info("   Press Ctrl+C to stop the server")
        logger.info("")
        
        from app import create_app
        app = create_app()
        
        # Run the application
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
