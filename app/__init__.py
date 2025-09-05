from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.offset import bp as offset_bp
    app.register_blueprint(offset_bp, url_prefix='/offset')
    
    from app.calibration import bp as calibration_bp
    app.register_blueprint(calibration_bp, url_prefix='/calibration')
    
    return app