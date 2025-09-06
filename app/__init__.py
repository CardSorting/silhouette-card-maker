import json
import os
import logging
from flask import Flask
from flask_cors import CORS
from app.config import config
from app.config_postgresql import postgresql_config
from app.models import init_db
from app.auth import init_auth


def _init_celery_worker(app):
    """Initialize Celery worker with comprehensive management"""
    start_celery_worker = os.environ.get('START_CELERY_WORKER', 'false').lower() == 'true'
    is_production = os.environ.get('FLASK_ENV', 'development') == 'production'
    
    if start_celery_worker:
        try:
            from app.celery_manager import worker_manager
            
            if is_production:
                app.logger.info("🚀 Production mode: Starting Celery worker with comprehensive management...")
            else:
                app.logger.info("🚀 Development mode: Starting Celery worker automatically...")
            
            # Configure worker based on environment
            concurrency = int(os.environ.get('CELERY_CONCURRENCY', 2))
            queues = os.environ.get('CELERY_QUEUES', 'pdf_generation,pdf_offset,default').split(',')
            
            success = worker_manager.start_worker(
                concurrency=concurrency,
                queues=queues,
                hostname=f"worker@{os.uname().nodename if hasattr(os, 'uname') else 'localhost'}",
                loglevel='info' if not is_production else 'warning'
            )
            
            if success:
                app.logger.info("✅ Celery worker started successfully with comprehensive management")
                app.logger.info(f"   Concurrency: {concurrency}")
                app.logger.info(f"   Queues: {', '.join(queues)}")
                app.logger.info("   Health monitoring: Enabled")
                app.logger.info("   Auto-restart: Enabled")
            else:
                app.logger.warning("⚠️ Failed to start Celery worker")
                app.logger.warning("   Celery tasks will fall back to threading mode")
                
        except Exception as e:
            app.logger.warning(f"⚠️ Failed to initialize Celery worker: {e}")
            app.logger.warning("   Celery tasks will fall back to threading mode")
            import traceback
            app.logger.debug(f"Full error: {traceback.format_exc()}")
    else:
        app.logger.info("ℹ️ Celery worker auto-start disabled")
        app.logger.info("   Set START_CELERY_WORKER=true to enable automatic worker startup")
        app.logger.info("   Or start manually with: python celery_app.py")


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    
    # Use PostgreSQL config if individual DB parameters are set
    if os.environ.get('DB_HOST'):
        app.config.from_object(postgresql_config[config_name])
        # Override the database URI with our custom engine
        from app.database import get_database_uri
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    else:
        app.config.from_object(config[config_name])
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    
    # Configure CORS for Next.js frontend
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize database
    init_db(app)
    
    # Initialize authentication system
    init_auth(app)
    
    # Initialize Celery worker if enabled
    _init_celery_worker(app)
    
    # Add custom template filters
    @app.template_filter('tojson')
    def tojson_filter(obj):
        return json.dumps(obj)
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.auth_routes import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.offset import bp as offset_bp
    app.register_blueprint(offset_bp, url_prefix='/offset')
    
    from app.calibration import bp as calibration_bp
    app.register_blueprint(calibration_bp, url_prefix='/calibration')
    
    from app.api.celery_routes import celery_bp
    app.register_blueprint(celery_bp, url_prefix='/api')
    
    # Add error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found', 'code': 'NOT_FOUND'}, 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return {'error': 'Method not allowed', 'code': 'METHOD_NOT_ALLOWED'}, 405
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {
            'error': 'Rate limit exceeded. Please try again later.',
            'code': 'RATE_LIMIT_EXCEEDED',
            'retry_after': str(e.retry_after)
        }, 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        return {'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}, 500
    
    # Add graceful shutdown handling
    @app.teardown_appcontext
    def cleanup_celery_worker(error):
        """Cleanup Celery worker on app shutdown"""
        if error:
            app.logger.error(f"App context teardown with error: {error}")
        
        # Only cleanup if this is the main process
        if os.environ.get('START_CELERY_WORKER', 'false').lower() == 'true':
            try:
                from app.celery_manager import worker_manager
                if worker_manager.is_worker_healthy():
                    app.logger.info("🧹 Cleaning up Celery worker on app shutdown...")
                    worker_manager.cleanup()
            except Exception as e:
                app.logger.warning(f"⚠️ Error during Celery worker cleanup: {e}")
    
    return app