"""
Configuration file for BioassayZone application
Supports development, testing, and production environments
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/bioassay.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10
    }
    
    # Security settings
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    REPORTS_FOLDER = 'reports'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/bioassay.log')
    
    # Audit logging
    AUDIT_LOG_RETENTION_DAYS = 365  # Keep audit logs for 1 year
    AUDIT_LOG_MAX_ENTRIES = 10000   # Maximum audit log entries
    
    # Password policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_HISTORY_SIZE = 10
    
    # Account lockout
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    # USP-81 compliance settings
    USP81_CONFIDENCE_LEVEL = 0.95
    USP81_MIN_ZONES_PER_CONCENTRATION = 3
    USP81_MAX_CV_PERCENT = 15.0
    
    # Report generation
    REPORT_TEMPLATE_PATH = 'templates/reports'
    REPORT_OUTPUT_FORMAT = 'pdf'  # pdf, html, csv
    
    # Email configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Redis configuration (for session storage and caching)
    REDIS_URL = os.environ.get('REDIS_URL')
    
    # Celery configuration (for background tasks)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
    
    # API rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '100 per minute'
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Monitoring and health checks
    HEALTH_CHECK_ENABLED = True
    METRICS_ENABLED = False  # Set to True to enable Prometheus metrics
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    
    # Development tools
    FLASK_DEBUG = True
    FLASK_ENV = 'development'


class TestingConfig(Config):
    """Testing configuration"""
    
    DEBUG = False
    TESTING = True
    
    # Test database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Test-specific settings
    LOG_LEVEL = 'DEBUG'
    AUDIT_LOG_RETENTION_DAYS = 1


class ProductionConfig(Config):
    """Production configuration"""
    
    DEBUG = False
    TESTING = False
    
    # Production security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    
    # Database connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'max_overflow': 20,
        'pool_size': 10
    }
    
    # Logging
    LOG_LEVEL = 'WARNING'
    
    # Performance
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Monitoring
    METRICS_ENABLED = True
    
    @classmethod
    def init_app(cls, app):
        """Initialize production application"""
        Config.init_app(app)
        
        # Production logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            # File handler
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                cls.LOG_FILE, 
                maxBytes=10240000, 
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('BioassayZone startup')


class DockerConfig(ProductionConfig):
    """Docker-specific configuration"""
    
    # Docker environment settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Health check endpoint
    HEALTH_CHECK_ENABLED = True
    
    # Container-specific logging
    LOG_LEVEL = 'INFO'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}
