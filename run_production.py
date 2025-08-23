#!/usr/bin/env python3
"""
Production startup script for BioassayZone
Handles environment configuration, logging, and server startup
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for production
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', '0')

# Import after setting environment
from app import app, db
from models import User
from config import config

def setup_logging():
    """Setup production logging"""
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        handlers=[
            logging.FileHandler('logs/bioassay.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set Flask logger level
    app.logger.setLevel(logging.INFO)
    
    # Log startup
    app.logger.info('BioassayZone production startup')

def setup_database():
    """Setup and verify database connection"""
    try:
        with app.app_context():
            # Test database connection
            with db.engine.connect() as conn:
                conn.execute(db.text("SELECT 1"))
            app.logger.info("Database connection successful")
            
            # Create tables if they don't exist
            db.create_all()
            app.logger.info("Database tables verified")
            
            # Check for admin user
            admin_user = db.session.query(User).filter(User.username == 'admin').first()
            if not admin_user:
                app.logger.warning("No admin user found. Please create one manually.")
            else:
                app.logger.info("Admin user found")
                
    except Exception as e:
        app.logger.error(f"Database setup failed: {e}")
        sys.exit(1)

def create_admin_user():
    """Create default admin user if none exists"""
    try:
        with app.app_context():
            admin_user = db.session.query(User).filter(User.username == 'admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@bioassay.local',
                    role='administrator'
                )
                admin_user.set_password('Admin123!')
                db.session.add(admin_user)
                db.session.commit()
                app.logger.info("Default admin user created: admin / Admin123!")
                app.logger.warning("⚠️  CHANGE THE DEFAULT ADMIN PASSWORD IMMEDIATELY!")
            else:
                app.logger.info("Admin user found")
                
    except Exception as e:
        app.logger.error(f"Failed to create admin user: {e}")

def main():
    """Main production startup function"""
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_name = os.environ.get('FLASK_CONFIG') or 'production'
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    app.logger.info(f"Loaded configuration: {config_name}")
    
    # Setup database
    setup_database()
    
    # Create admin user if needed
    create_admin_user()
    
    # Log configuration summary
    app.logger.info(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.logger.info(f"Debug mode: {app.config['DEBUG']}")
    app.logger.info(f"Testing mode: {app.config['TESTING']}")
    
    # Start the application
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    app.logger.info(f"Starting BioassayZone on {host}:{port}")
    
    if __name__ == '__main__':
        app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main()
